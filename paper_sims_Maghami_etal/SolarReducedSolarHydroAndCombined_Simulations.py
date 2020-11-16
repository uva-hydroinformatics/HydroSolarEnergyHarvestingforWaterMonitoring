import turbine
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


def timezone_translator_formasking(tz):
    return {
        'US/Eastern': '-0500',
        'US/Central': '-0600',
        'US/Mountain': '-0700',
        'US/Pacific': '-0800'
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
# ---------------------- Solar, reduced Solar, reduced Solar + Hydro--------------------------------
# --------------------------------------------------------------------------------------------------
# Read the concatenated solar data which includes 2010-2014 period for 44 USGS sites as a dataframe
Solar_ConcatData_dir = os.path.join(os.path.dirname(__file__), './data_files/Solar_data_files/concatenate_')

# Read file containing USGS siteID and lat-lon from SolarAnywhere.
Site_IDCoordinates_file = os.path.join(os.path.dirname(__file__), './data_files/USGS_Sites_12_10_2019_42sites_INFOandMissingReportMerged.csv')
df_ = pd.read_csv(Site_IDCoordinates_file, encoding="ISO-8859-1", dtype={'site_no': str},
                  usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])

Solar_Data_files = [f for f in os.listdir('./data_files/Solar_data_files') if
              os.path.isfile(os.path.join('./data_files/Solar_data_files', f)) and 'csv' in f]

USGS_Sites_list = [i.split('_')[1].split('.')[0] for i in Solar_Data_files]


# Search for all flow data files in the folder (txt files)
Hydro_Data_files = [f for f in os.listdir('./data_files/Hydro_data_files/Processed_data') if
              os.path.isfile(os.path.join('./data_files/Hydro_data_files/Processed_data', f)) and 'txt' in f]

# Print information on data found
print("Hydro Files found(" + str(len(Hydro_Data_files)) + "):")
print(Hydro_Data_files)


# TODO: Altitude must be corrected from USGS website
# TODO: timezone must be corrected
coordinates = [] # latitude, longitude, USGSSiteID, altitude, tz
for i, site in enumerate(USGS_Sites_list):
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
Sampling_interval = 1 # Time between two wake up events
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
dc_reduced_power = []
dc_reduced_evg_power = []
selected_sites = []

#  Used for "Backup: Some Informative Plots", uncomment if need to explore the input weather data
# temp = []
# GHI_list = []
# DNI_list = []
# DHI_list = []
# Wind_list = []


print('Simulation has begun...')
# Important: Double check with PVLIB documentation to see how they model based on the cloudysky data
jj = 0
for latitude, longitude, USGSSiteID, altitude, tz in coordinates:
    # if USGSSiteID == '04092750' or USGSSiteID =='05537980' or USGSSiteID =='04165710':
    if USGSSiteID == '04165710':
        jj += 1
        print(jj)
        df = pd.read_csv(Solar_ConcatData_dir + USGSSiteID + '.csv', encoding="ISO-8859-1", dtype={'site_no': str})

        df['Date_Time'] = pd.to_datetime(df['Date_Time']) + pd.Timedelta(timezone_translator_toUTCminusLocaltime(tz))
        df['Date_Time'] = df.apply(lambda x: pd.Timestamp(x['Date_Time'], tz='UTC'), axis=1)
        df.set_index('Date_Time', inplace=True)
        df.index = df.index.tz_convert(tz)

        # # '2010-03-14 02:00:00'
        # df['TimeStamp'] = df.apply(lambda x: pd.Timestamp(x['Date_Time'], tz='US/Eastern'), axis=1)
        # df.set_index('TimeStamp', inplace=True)

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
        # tl = pvlib.clearsky.lookup_linke_turbidity(times, latitude, longitude)
        # cs = pvlib.clearsky.ineichen(solpos['apparent_zenith'], am_abs, tl,
        #                              dni_extra=dni_extra, altitude=altitude)
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
                dc.loc[dc.index.date == datetime.date(year, month, 1), 'power_reduction_factor'] = monthly_reduction_list[month-1]

        dc = dc.interpolate(method='linear')
        dc['p_mp_reduced'] = dc['p_mp']*dc['power_reduction_factor']

        dc_reduced_list = dc['p_mp_reduced'].tolist()
        dc_reduced_power.append(dc['p_mp_reduced'])

        # # Used for "Backup: Some Informative Plots", uncomment if need to explore the input weather data
        # temp.append(temps['temp_cell'])


        # Evergreen forest, extreme , only 0.05 percent of the power:
        dc['p_mp_reduced_evg'] = dc['p_mp'] * 0.04
        dc_reduced_evg_list = dc['p_mp_reduced_evg'].tolist()
        dc_reduced_evg_power.append(dc['p_mp_reduced_evg'])




        # Solar without any tree canopy
        print('\nSolar without any tree canopy')

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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)

        print('Time spent to simulate: ', datetime.datetime.now() - now)

        # Percentage_offTime = (100.0 * Total_Off_Time) / Total_time
        # Percentage_Joules_overflow = 60 * Total_Overflow / Total_energy
        #
        # Percentage_offTime_list.append(Percentage_offTime)
        # Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)
        energy_list.append(sum(dc_list))  # Accumulate power and append to a list



        # Solar with tree canopy (decidouos)
        print('\nSolar with tree canopy (decidouos)')

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

        [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, dc_reduced_list, T_threshold,
                                                                                 verbose=True)

        Eh = [x / 60.0 for x in dc_reduced_list]  # convert watt-min to watt-hour
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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)

        print('Time spent to simulate: ', datetime.datetime.now() - now)
        energy_list.append(sum(dc_reduced_list))  # Accumulate power and append to a list



        # Solar with tree canopy (evergreen, extreme)
        print('\nSolar with tree canopy (evergreen, extreme)')

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

        [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, dc_reduced_evg_list, T_threshold,
                                                                                 verbose=True)

        Eh = [x / 60.0 for x in dc_reduced_evg_list]  # convert watt-min to watt-hour
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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)

        print('Time spent to simulate: ', datetime.datetime.now() - now)
        energy_list.append(sum(dc_reduced_evg_list))  # Accumulate power and append to a list


        # Hydro only
        print('\nHydro only')
        USGS_site_file = 'time_zone_converted_' + USGSSiteID + '_72255.txt'
        print("Reading file: " + USGS_site_file)

        flow_velocity_file = os.path.join(os.path.dirname(__file__),
                                          './data_files/Hydro_data_files/Processed_data/' + USGS_site_file)
        df = pd.read_csv(flow_velocity_file)

        df['timestamp'] = df.apply(lambda x: pd.Timestamp(x['timestamp'], tz=tz), axis=1)
        df.set_index('timestamp', inplace=True)

        mask = (df.index >= ('2010-01-01 01:00:00' + timezone_translator_formasking(tz))) & \
               (df.index <= ('2015-01-01 00:00:00' + timezone_translator_formasking(tz)))

        df = df.loc[mask]

        upsampled = df.resample('1T')
        # print(upsampled.head(61))
        interpolated = upsampled.interpolate(method='linear')
        # print(interpolated.head(61))
        print('interpolated')

        minutes = []
        for i in range(0, len(interpolated.index)):
            minutes.append(int(((abs(interpolated.index[i] - interpolated.index[0])).total_seconds()) / 60))

        Total_time1 = minutes[-1] - minutes[0]
        # flow_velocity = interpolated['flow'].tolist()
        total_sim_steps = minutes[-1]  # in minutes

        # Creation of vectors to be used in the simulation
        Eh = np.zeros(total_sim_steps)
        Ebat_in = np.zeros(total_sim_steps)
        Ebat_out = np.zeros(total_sim_steps)
        B = np.zeros(total_sim_steps)
        Eload = np.zeros(total_sim_steps)
        Overflow = np.zeros(total_sim_steps)

        gen_power_hydro = turbine.waterlilyv2(interpolated)
        gen_power_hydro = gen_power_hydro['power'].tolist()

        gen_power_hydro = [power * 2 for power in gen_power_hydro]  # Use two WaterLily

        T_threshold = 24 * 60  # 1 day (in minutes) it is used when interpolating the missing data, if the gap is greater than one
        # day, the gap is ignored
        [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, gen_power_hydro, T_threshold,
                                                                                 verbose=True)

        Eh = [x / 60.0 for x in gen_power_hydro]  # convert watt-min to watt-hour
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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)
        energy_list.append(sum(gen_power_hydro))  # Accumulate power and append to a list



        # Hydro + reduced Solar (deciduous tree canopy)
        print('\nHydro + reduced Solar (deciduous tree canopy)')
        # gen_power_solar = [x / myInt for x in gen_power_solar]
        gen_power_hydro_reduced_solar = [a + b for a, b in zip(gen_power_hydro, dc_reduced_list)]

        T_threshold = 24 * 60  # 1 day (in minutes) it is used when interpolating the missing data, if the gap is greater than one
        # day, the gap is ignored
        [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, gen_power_hydro_reduced_solar, T_threshold,
                                                                                 verbose=True)

        Eh = [x / 60.0 for x in gen_power_hydro_reduced_solar]  # convert watt-min to watt-hour
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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)
        energy_list.append(sum(gen_power_hydro_reduced_solar))  # Accumulate power and append to a list

        print(datetime.datetime.now() - now, '\n')


        # Hydro + reduced Solar (evergreen tree canopy, extreme)
        print('\nHydro + reduced Solar (evergreen tree canopy, extreme)')
        # gen_power_solar = [x / myInt for x in gen_power_solar]
        gen_power_hydro_reduced_solar_evg = [a + b for a, b in zip(gen_power_hydro, dc_reduced_evg_list)]

        T_threshold = 24 * 60  # 1 day (in minutes) it is used when interpolating the missing data, if the gap is greater than one
        # day, the gap is ignored
        [step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, gen_power_hydro_reduced_solar_evg, T_threshold,
                                                                                 verbose=True)

        Eh = [x / 60.0 for x in gen_power_hydro_reduced_solar_evg]  # convert watt-min to watt-hour
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

        fraction_overflow = sum(Overflow) / (
                    sum(Nbat_in * Ncc * Eh) + 0.000000000000001)  # Added to avoid div by 0 in case
        print("Percentage overflow: {:.2%}".format(fraction_overflow))

        fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
        print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

        Percentage_offTime_list.append(100 * fraction_sampleloss)
        Percentage_Joules_overflow_list.append(fraction_overflow)
        energy_list.append(sum(gen_power_hydro_reduced_solar_evg))  # Accumulate power and append to a list

        print(datetime.datetime.now() - now, '\n')

        selected_sites.append(USGSSiteID)


Avg_harvestable_Energy_list = [x / 2629380.0 * 60.0 * 5.0 for x in energy_list] # W.hr *  60 Jouls/(1W.min)  * 5min/1min => Avg harvestable Energy in 5 minutes (x/ ???? => ????= minutes of simulation)
