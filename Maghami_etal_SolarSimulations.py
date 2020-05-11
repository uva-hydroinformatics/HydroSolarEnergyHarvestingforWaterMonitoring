# Imports all modules needed for this code
from context import battery
from context import communication
from context import controller
from context import sensor
from context import station
from context import core

# Imports other required modules for this code
import pandas as pd
import os
import numpy as np
import datetime
import pvlib


def timezone_translator_toUTCminusLocaltime(tz):
    return {
        'US/Eastern': '05:00:00',
        'US/Central': '06:00:00',
        'US/Mountain': '07:00:00',
        'US/Pacific': '08:00:00',
    }.get(tz, None)


now = datetime.datetime.now()


# Read the concatenated solar data which includes 2010-2014 period for 42 USGS sites as a dataframe
Solar_data_files_dir = os.path.join('./', 'data_files/solar_data_files/solar_')

df_solar = pd.read_csv(os.path.join('./', 'data_files/USGS_Sites_Info_12_7_2019.txt'), encoding="ISO-8859-1", sep='\t',
				  dtype={'site_no': str, 'parm_cd': str, 'huc_cd': str}, usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])


USGS_Sites_list = df_solar['site_no'].tolist()

# TODO: Altitude must be corrected from USGS website
coordinates = []  # latitude, longitude, USGSSiteID, altitude, tz
for i, site in enumerate(USGS_Sites_list):
# latitude, longitude, USGSSiteID, altitude, timezone (must be corrected)
	coordinates.append((round(float(df_solar['dec_lat_va'][i]), 3), round(float(df_solar['dec_long_va'][i]), 3), site, 0,
						df_solar['Time_zone'][i]))


# get the module and inverter specifications from S
sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module = sandia_modules['Kyocera_Solar_KS20__2008__E__']
inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_']

system = {'module': module, 'inverter': inverter, 'surface_azimuth': 180}


# create empty list to append the filename in the target USGS observation data directory
Mean_Energy_list = []
Missing_samples_percent_list = []
Percentage_Joules_overflow_list = []
dc_power = []


jj = 0
for latitude, longitude, USGSSiteID, altitude, tz in coordinates:
	jj += 1
	print('\n', '*'*40)
	print(jj, ': Simulating solar for: ',  USGSSiteID)


	df = pd.read_csv(Solar_data_files_dir + USGSSiteID + '.csv', encoding="ISO-8859-1", dtype={'site_no': str})

	df['Date_Time'] = pd.to_datetime(df['Date_Time']) + pd.Timedelta(timezone_translator_toUTCminusLocaltime(tz))
	df['Date_Time'] = df.apply(lambda x: pd.Timestamp(x['Date_Time'], tz='UTC'), axis=1)
	df.set_index('Date_Time', inplace=True)
	df.index = df.index.tz_convert(tz)

	upsampled = df.resample('1T')
	# print(upsampled.head(61))

	interpolated = upsampled.interpolate(method='linear')
	# print(interpolated.head(61))
	print('interpolated')

	# interpolated = df

	minutes = []
	for i in range(0, len(interpolated.index)):
		minutes.append(int(((abs(interpolated.index[i] - interpolated.index[0])).total_seconds()) / 60))

	Total_time1 = minutes[-1] - minutes[0]

	times = interpolated.index
	system['surface_tilt'] = latitude
	solpos = pvlib.solarposition.get_solarposition(times, latitude, longitude)
	dni_extra = pvlib.irradiance.get_extra_radiation(times)
	dni_extra = pd.Series(dni_extra, index=times)
	airmass = pvlib.atmosphere.get_relative_airmass(solpos['apparent_zenith'])
	pressure = pvlib.atmosphere.alt2pres(altitude)
	am_abs = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
	aoi = pvlib.irradiance.aoi(system['surface_tilt'], system['surface_azimuth'],
							   solpos['apparent_zenith'], solpos['azimuth'])
	total_irrad = pvlib.irradiance.get_total_irradiance(system['surface_tilt'],
														system['surface_azimuth'],
														solpos['apparent_zenith'],
														solpos['azimuth'],
														interpolated['DNI (W/m^2))'], interpolated['GHI (W/m^2)'],
														interpolated['DHI (W/m^2)'],
														# Later on, remove extra closing parentheses in 'DNI (W/m^2))',
														# codes in solar data preparation contains the mistake

														dni_extra=dni_extra,
														model='haydavies')  # Can also vary albedo
	temps = pvlib.pvsystem.sapm_celltemp(total_irrad['poa_global'],
										 interpolated['Wspd (m/s)'], interpolated['Dry-bulb (C)'])
	effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
		total_irrad['poa_direct'], total_irrad['poa_diffuse'],
		am_abs, aoi, module)
	dc = pvlib.pvsystem.sapm(effective_irradiance, temps['temp_cell'], module)
	dc.fillna(0, inplace=True)  # Nan values are filled with zero
	dc_list = dc['p_mp'].tolist()
	dc_power.append(dc['p_mp'])


	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(18.0/(60.0*1), 4, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on
	# (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor],
								   operation_mode='fixed_battsense', verbose=True)

	# Runs discrete-time simulation
	dc_ = pd.DataFrame({'power': dc.p_mp})  # Added to convert series to dataframe
	simulation_output = core.runsim(dc_, sensor_station, batt, verbose = True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output['generated energy'].mean() * 3600*1000 * 5 # Convert from kwh to J and in a 5-minute
	# window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = dc_.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (Total_energy + 0.000000000000001)  # Add not to div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)
	# energy_list.append(sum(dc_list))  # Accumulate power and append to a list

	print('\nSimulation time so far: ', datetime.datetime.now() - now)


df_solar['MeanEnergy_Solar'] = Mean_Energy_list  # in 5 minutes
df_solar['PerOfftime_Solar'] = Missing_samples_percent_list
df_solar['PerjoulOvFl_Solar'] = Percentage_Joules_overflow_list


df_solar.to_csv(os.path.join('./', 'results/Solar_Simulation.csv'), sep=',')

