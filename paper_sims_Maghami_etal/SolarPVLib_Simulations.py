import os
import statistics
import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
sns.set_color_codes()
import pvlib
import datetime

def timezone_translator_toUTCminusLocaltime(tz):
    return {
        'US/Eastern': '05:00:00',
        'US/Central': '06:00:00',
        'US/Mountain': '07:00:00',
        'US/Pacific': '08:00:00',
    }.get(tz, None)

def StepEnergy(minutes, Gen_power, T_threshold, verbose=True):

    dt=0
    delta_t=[]
    step_energy=[]
    for i in range(1,len(minutes)):
        dt = minutes[i]-minutes[i-1]
        if dt<T_threshold:
            step_energy.append((Gen_power[i-1]+Gen_power[i])*dt*60/2)
            delta_t.append(dt)
        else:
            step_energy.append(0)
            delta_t.append(0)
            print("ignored!")

    Total_time=sum(delta_t)
    Total_energy=sum(step_energy)
    Average_Energy=Total_energy/Total_time

    if verbose==True:
        print("Total time(months): "+str(Total_time/(30*24*60)))
        print("Total energy(kwh): "+str(Total_energy/3600000))
        print("Average energy(Joules in one minute step): "+str(Average_Energy))


    return [step_energy, Total_time,Total_energy, Average_Energy]


now=datetime.datetime.now()
# --------------------------------------------------------------------------------------------------
# ------------------------------- Solar data to Solar power-----------------------------------------
# --------------------------------------------------------------------------------------------------
# Read the concatenated solar data which includes 2010-2014 period for 44 USGS sites as a dataframe
Solar_ConcatData_dir = os.path.join(os.path.dirname(__file__), './data_files/Solar_data_files/concatenate_')


# Read file containing USGS siteID and lat-lon from SolarAnywhere.
Site_IDCoordinates_file = os.path.join(os.path.dirname(__file__), './data_files/USGS_Sites_12_10_2019_42sites_INFOandMissingReportMerged.csv')
df_ = pd.read_csv(Site_IDCoordinates_file, encoding="ISO-8859-1", dtype={'site_no': str},
                  usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])

Data_files = [f for f in os.listdir('./data_files/Solar_data_files') if
              os.path.isfile(os.path.join('./data_files/Solar_data_files', f)) and 'csv' in f]

USGS_Sites_list = [i.split('_')[1].split('.')[0] for i in Data_files]


# TODO: Altitude must be corrected from USGS website
coordinates = [] # latitude, longitude, USGSSiteID, altitude, tz
for i, site in enumerate(USGS_Sites_list):
    # latitude, longitude, USGSSiteID, altitude, timezone (must be corrected)
    coordinates.append((round(float(df_['dec_lat_va'][i]), 3), round(float(df_['dec_long_va'][i]), 3), site, 0, df_['Time_zone'][i]))


# get the module and inverter specifications from S
sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module = sandia_modules['Kyocera_Solar_KS20__2008__E__']
inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_']

system = {'module': module, 'inverter': inverter, 'surface_azimuth': 180}



# Simulations parameters
Nbat_in = 0.9 # battery's charge efficiency
Nbat_out = 0.7 # battery's discharge efficiency
Bnom = (1/Nbat_out)*400 # in Wh
Binit = 1.0*Bnom # in Wh
# Eleak = 0 # in Wh
Eleak = 0.66/3600 # in Wh (2% self-discharge in one month=> 0.02*400Wh/(30days*24days*60min)
Psleep = 3.7*60*(10**-6) # Power when system is in idle/sleep mode


Ncc = 0.9 # charge controller efficiency
Bth = 0.3*Bnom # battery charge threshold to turn back on after power failure
Batt_status = 1 # initial status of the battery is on

# rho = 1/60 # step is one minute (conversion factor w to wh)
# Pcc = 0 # Power dissipated by the charge controller
# Pvr = 0 # Power dissipated by the voltage regulator
# Psys = 14.38 # Power consumption of electronic components (controller, sensor and communications)
# T_on = 1 # Time the station remains on (used to calculate average energy consumption)
Sampling_interval = 5 # Time between two wake up events
Communication_interval = 24 * Sampling_interval # We communicate the samples every 24 measurement
#
# Duty_cycle = T_on/Sampling_interval # Duty cycle (fraction of the time the system stays on)
# sumDCsysPsys = Duty_cycle*Psys # Average power consumption of the system
#
# # Equations available on page 73 of the reference paper
#
# Eload_setup = rho*(Pcc+Pvr+sumDCsysPsys) # target power consumption for the load
Eload_setup = (14.38*60/(Sampling_interval*60) + 60*Psleep*(1-9/(Sampling_interval*60)-60/(Communication_interval*60)))/3600



T_threshold = 24*60
gen_power = []
energy_list = []
Percentage_offTime_list = []
Percentage_Joules_overflow_list = []


energies = {}
dc_power = []


print('Simulation has begun...')
# Important: Double check with PVLIB documentation to see how they model based on the cloudysky data
jj = 0
for latitude, longitude, USGSSiteID, altitude, tz in coordinates:

    jj += 1
    print(jj)
    df = pd.read_csv(Solar_ConcatData_dir + USGSSiteID + '.csv', encoding="ISO-8859-1", dtype={'site_no': str})

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
                                               interpolated['DNI (W/m^2))'], interpolated['GHI (W/m^2)'], interpolated['DHI (W/m^2)'],
                                                        #Later on, Take care of extra closing paranteses in 'DNI (W/m^2))',
                                                        # codes in solar data preparation contains the mistake

                                               dni_extra=dni_extra,
                                               model='haydavies')  # Can also vary albedo
    temps = pvlib.pvsystem.sapm_celltemp(total_irrad['poa_global'],
                                         interpolated['Wspd (m/s)'], interpolated['Dry-bulb (C)'])
    effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
         total_irrad['poa_direct'], total_irrad['poa_diffuse'],
         am_abs, aoi, module)
    dc = pvlib.pvsystem.sapm(effective_irradiance, temps['temp_cell'], module)
    # ac = pvlib.pvsystem.snlinverter(dc['v_mp'], dc['p_mp'], inverter)
    dc.fillna(0, inplace=True) # Nan values are filled with zero
    dc_list = dc['p_mp'].tolist()
    dc_power.append(dc['p_mp'])

    total_sim_steps = minutes[-1]  # in minutes

    # Creation of vectors to be used in the simulation
    Eh = np.zeros(total_sim_steps)
    Ebat_in = np.zeros(total_sim_steps)
    Ebat_out = np.zeros(total_sim_steps)
    B = np.zeros(total_sim_steps)
    Eload = np.zeros(total_sim_steps)
    Overflow = np.zeros(total_sim_steps)

    T_threshold = 24 * 60  # 1 day (in minutes) it is used when interpolating the missing data, if the gap is greater than one
    # day, the gap is ignored

    [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, dc_list, T_threshold,
                                                                             verbose=True)


    Eh = [x / 60.0 for x in dc_list]  # convert watt-min to watt-hour
    Eh = np.asarray(Eh)

    # initial conditions
    Eload[0] = Eload_setup
    Ebat_out[0] = (Eload[0] / Nbat_out) + Eleak
    Ebat_in[0] = min(Nbat_in * Ncc * Eh[0], max(0, Nbat_out * Bnom - Binit - Ebat_out[0]))
    B[0] = max(0, min(Nbat_out * Bnom, Binit + Ebat_in[0] - Ebat_out[0]))
    Overflow[0] = max(0, Nbat_in * Ncc * Eh[0] - Ebat_in[0])

    for k in range(1, total_sim_steps):

        Eload[k] = Batt_status * Eload_setup

        Ebat_out[k] = (Eload[k] / Nbat_out) + Eleak

        # original version: Ebat_in[d] = min(Nbat_in * Epv(d,omega),min(0,Nbat_out*Bnom - B[d-1] - Ebat_out[d]))
        Ebat_in[k] = min(Nbat_in * Ncc * Eh[k], max(0, Nbat_out * Bnom - B[k - 1] - Ebat_out[k]))

        B[k] = max(0, min(Nbat_out * Bnom, B[k - 1] + Ebat_in[k] - Ebat_out[k]))

        Overflow[k] = max(0, Nbat_in * Ncc * Eh[k] - Ebat_in[k])

        if B[k] == 0:
            Batt_status = 0
            Eload[k] = 0
        if (Batt_status == 0) and (B[k] >= Bth):
            Batt_status = 1

    fraction_overflow = sum(Overflow) / (sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
    print("Percentage overflow: {:.2%}".format(fraction_overflow))

    fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
    print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

    Percentage_offTime_list.append(100 * fraction_sampleloss)
    Percentage_Joules_overflow_list.append(fraction_overflow)

    print('Time spent to simulate: ', datetime.datetime.now() - now)
    energy_list.append(sum(dc_list))  # Accumulate power and append to a list

    print(datetime.datetime.now() - now, '\n')


Avg_harvestable_Solar_Energy_list = [x / 2629380.0 * 60.0 * 5.0 for x in energy_list] # W.hr *  60 Jouls/(1W.min)  * 5min/1min => Avg harvestable Energy in 5 minutes (x/ ???? => ????= minutes of simulation)

df_['Avg5minSolarHarEnergy'] = Avg_harvestable_Solar_Energy_list
df_['PerOfftime_solar'] = Percentage_offTime_list
df_['PerjoulOvFl_solar'] = Percentage_Joules_overflow_list

df_.to_csv(os.path.join('./', 'results/Solar_Simulation.csv'), sep=',')