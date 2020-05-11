# Imports all modules needed for this example
from context import timeseries
from context import turbine
from context import battery
from context import communication
from context import controller
from context import sensor
from context import station
from context import core

# Imports other required modules for this code
import pandas as pd
import os
import matplotlib.pyplot as plt
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

df_ = pd.read_csv(os.path.join('./', 'data_files/USGS_Sites_Info_the_three_sites.txt'), encoding="ISO-8859-1", sep='\t',
				  dtype={'site_no': str, 'parm_cd': str, 'huc_cd': str}, usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])

USGS_Sites_list = df_['site_no'].tolist()

# TODO: Altitude must be corrected from USGS website
# TODO: Actually, the nearby sites (those in same SolarAnywhere 10-km grid) their location is considered the same as the nearby sites
# TODO: timezone must be corrected
coordinates = []  # latitude, longitude, USGSSiteID, altitude, tz
for i, site in enumerate(USGS_Sites_list):
# latitude, longitude, USGSSiteID, altitude, timezone (must be corrected)
	coordinates.append((round(float(df_['dec_lat_va'][i]), 3), round(float(df_['dec_long_va'][i]), 3), site, 0, df_['Time_zone'][i]))


# get the module and inverter specifications from S
sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module = sandia_modules['Kyocera_Solar_KS20__2008__E__']
inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_']

system = {'module': module, 'inverter': inverter, 'surface_azimuth': 180}





Sensor_P_active = 18.0 * 2 / 60.0  # Watts All sensors + communication
Sensor_T_idle = 1

counter = 0
for latitude, longitude, USGSSiteID, altitude, tz in coordinates:
	counter += 1
	print('\n', '*'*40)
	print(counter, ': Simulating solar for: ',  USGSSiteID)

	Mean_Energy_list = []
	Missing_samples_percent_list = []
	Percentage_Joules_overflow_list = []
	dc_power = []

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
														# Later on, Take care of extra closing paranteses in 'DNI (W/m^2))',
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

	# Here the changes in solar harvested power due to dense tree canopy is made:
	# Assumption: It is assumed that in the first day of each month a reduction factor is given (no variation across
	# time in the first days of months), then for any other time and days other than these first days of each month,
	# the reduction factor is linearly interpolated. Please note that this reduction curve is an estimate of what
	# Chikita (2018), Garner et. al (2014; 2017) has done with the exception that in their works this reduction curve
	# is for net solar radiation; however, since it is really hard to estimate the effect of shade caused by tree
	# canopy shading on DHI, DNI, GHI, wind speed and temperature, we implemented that curve directly on the power
	# output that we get from PVlib.
	# monthly_reduction_list estimate is based on the temporal variation of shading factor reported by Chikita
	# (2018) and combining it with the shading factor and reduced
	# net solar radiation relationship presented by Garner et. al (2017)

	dc['power_reduction_factor'] = np.nan

	monthly_reduction_list = [0.45, 0.45, 0.45, 0.45, 0.25, 0.14, 0.08, 0.07, 0.05, 0.08, 0.25, 0.45]  # Jan:Dec
	for year in range(2010, 2016, 1):
		for month in range(1, 13, 1):
			dc.loc[dc.index.date == datetime.date(year, month, 1), 'power_reduction_factor'] = monthly_reduction_list[
				month - 1]

	dc = dc.interpolate(method='linear')
	dc['p_mp_reduced'] = dc['p_mp'] * dc['power_reduction_factor']
	# Evergreen forest, extreme , only 0.05 percent of the power:
	dc['p_mp_reduced_evg'] = dc['p_mp'] * 0.04




	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Solar without any tree canopy
	# Runs discrete-time simulation
	dc_1 = pd.DataFrame({'power': dc.p_mp})  # Added to convert series to dataframe
	simulation_output = core.runsim(dc_1, sensor_station, batt, verbose = True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output['generated energy'].mean() * 3600*1000 * 5 # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = dc_1.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (Total_energy + 0.000000000000001)  # Added to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)
	# energy_list.append(sum(dc_list))  # Accumulate power and append to a list



	print('\nSolar with tree canopy (decidouos)')
	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Solar with tree canopy (decidouos)
	# Runs discrete-time simulation
	dc_2 = pd.DataFrame({'power': dc.p_mp_reduced})  # Added to convert series to dataframe
	simulation_output = core.runsim(dc_2, sensor_station, batt, verbose=True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output[
					  'generated energy'].mean() * 3600 * 1000 * 5  # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = dc_2.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (
				Total_energy + 0.000000000000001)  # Added to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)
	# energy_list.append(sum(dc_list))  # Accumulate power and append to a list


	print('\nSolar with tree canopy (evergreen, extreme)')
	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Solar with tree canopy (evergreen, extreme)
	# Runs discrete-time simulation
	dc_3 = pd.DataFrame({'power': dc.p_mp_reduced_evg})  # Added to convert series to dataframe
	simulation_output = core.runsim(dc_3, sensor_station, batt, verbose=True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output[
					  'generated energy'].mean() * 3600 * 1000 * 5  # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = dc_3.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (
				Total_energy + 0.000000000000001)  # Added to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)
	# energy_list.append(sum(dc_list))  # Accumulate power and append to a list



	print('\nHydro only')
	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Hydro only
	try:
		# Reads the pickle dataframe
		flow_df = pd.read_pickle(os.path.join('./data_files/hydro_data_files/', USGSSiteID + '_72255_UTC.pkl'))
	except:
		print("File  could not be found!")  # To be edited


	mask = (flow_df.index >= pd.Timestamp('2010-01-01 00:00:00', tz='GMT')) & (
				flow_df.index <= pd.Timestamp('2015-01-01 00:00:00', tz='GMT'))
	flow_df = flow_df.loc[mask]

	# Creates an one-minute linearly interpolated time series
	resampled_flow_df = timeseries.resampledf(flow_df, interp_method='linear', verbose=True)

	# Creates power time series based on first version of water lily turbine model
	power_df = turbine.waterlilyv1(resampled_flow_df, verbose=False)


	# Runs discrete-time simulation
	simulation_output = core.runsim(power_df, sensor_station, batt, verbose=True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output[
					  'generated energy'].mean() * 3600 * 1000 * 5  # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = power_df.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (
				Total_energy + 0.000000000000001)  # Added to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)



	print('\nHydro + reduced Solar (deciduous tree canopy)')
	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Hydro + reduced Solar (deciduous tree canopy)
	df_hyd_dectree = (power_df + dc_2)

	# Runs discrete-time simulation
	simulation_output = core.runsim(df_hyd_dectree, sensor_station, batt, verbose=True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output[
					  'generated energy'].mean() * 3600 * 1000 * 5  # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = df_hyd_dectree.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (
				Total_energy + 0.000000000000001)  # Add to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)



	print('\nHydro + reduced Solar (evergreen tree canopy, extreme)')
	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(Sensor_P_active, Sensor_T_idle, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)


	# Hydro + reduced Solar (evergreen tree canopy, extreme)
	df_hyd_evertree = (power_df + dc_3)

	# Runs discrete-time simulation
	simulation_output = core.runsim(df_hyd_evertree, sensor_station, batt, verbose=True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output[
					  'generated energy'].mean() * 3600 * 1000 * 5  # Convert from kwh to J and in a 5-minute window
	Mean_Energy_list.append(Mean_Energy)

	# Calculate missing sample ratio due to power outage
	successful_samples = sensor_station.sensordata()[0]['sample count']
	total_sim_steps = df_hyd_evertree.shape[0]
	expected_samples = np.floor(total_sim_steps / sensor_station.sensordata()[0]['sampling interval'])
	Missing_samples_percent = 100 * (expected_samples - successful_samples) / expected_samples
	Missing_samples_percent_list.append(Missing_samples_percent)

	# Calculate energy overflow ratio dut to battery saturation
	Total_energy_overflow = batt.overflow_energy
	Total_energy = simulation_output['generated energy'].sum()
	# Total_energy = power_df['generated energy'].sum()
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (
			Total_energy + 0.000000000000001)  # Added to avoid div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)

	Scenario_list = ['Solar', 'Solar with tree canopy (decidouos)', 'Solar with tree canopy (evergreen, extreme)',
			'Hydro only', 'Hydro + reduced Solar (deciduous tree canopy)',
			'Hydro + reduced Solar (evergreen tree canopy, extreme)']
	output_df = pd.DataFrame(
		{'Scenario': Scenario_list,
		 'Percentage_Joules_overflow': Percentage_Joules_overflow_list,
		 'Missing_samples_percent': Missing_samples_percent_list,
		 'Mean_Energy_in5min': Mean_Energy_list}
	)

	output_df.set_index('Scenario', inplace=True)

	output_df.to_csv(os.path.join('./', 'results/EnergyHarvestingScenarios_' + USGSSiteID + '.csv'))

	print('\nSimulation time so far: ', datetime.datetime.now() - now)



