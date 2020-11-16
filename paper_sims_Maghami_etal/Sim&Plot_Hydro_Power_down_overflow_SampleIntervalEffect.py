import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import statistics
import turbine
from scipy import stats


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


print("Loading configurations...")

# create empty list to append the filename in the target USGS observation data directory
median_genpower = []
mean_genpower = []
Mean_Energy_list = []
Total_time_list = []
Percentage_offTime_list = []
Percentage_Joules_overflow_list = []
Average_Energy_list = []


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


File_name = os.path.join(os.path.dirname(__file__), './data_files/Hydro_data_files/Processed_data/time_zone_converted_04092750_72255.txt')
timezone ='US/Eastern'
# 04092750
# 05537980
# 04165710

df = pd.read_csv(File_name)

df['timestamp'] = df.apply(lambda x: pd.Timestamp(x['timestamp'], tz=timezone), axis=1)
df.set_index('timestamp', inplace=True)

mask = (df.index >= ('2010-01-01 01:00:00' + timezone_translator_formasking(timezone))) & \
       (df.index <= ('2015-01-01 00:00:00' + timezone_translator_formasking(timezone)))

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

gen_power = turbine.waterlilyv2(interpolated)
gen_power = gen_power['power'].tolist()

gen_power = [power * 2 for power in gen_power]  # Use two WaterLily

T_threshold = 24 * 60  # 1 day (in minutes) it is used when interpolating the missing data, if the gap is greater than one
# day, the gap is ignored
[step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, gen_power, T_threshold,
                                                                         verbose=True)

Average_Energy_list.append(Average_Energy * Sampling_interval)

Eh = [x / 60.0 for x in gen_power]  # convert watt-min to watt-hour
Eh = np.asarray(Eh)

Total_time_list.append(total_sim_steps / (24.0 * 60.0))  # convert from minutes to days
# Mean_Energy_list.append(Mean_Energy)
# genpower_list.append(gen_power)
median_genpower.append(statistics.median(gen_power))
mean_genpower.append(statistics.mean(gen_power))


Percentage_offTime_list=[]
Percentage_Joules_overflow_list = []

print("Initializing simulations...")

T_threshold = 24*60*100
[step_energy, Total_time, Total_energy, Average_Energy] = StepEnergy(minutes, gen_power, T_threshold,
                                                                         verbose=True)

# Sensor_samplinginterval = [1, 2, 3, 4, 5, 10, 15, 20, 25, 26, 27, 28, 29, 30, 40, 50, 60]
# Sensor_samplinginterval = [1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 60]
Sensor_samplinginterval = [1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 51, 52, 53, 54, 55, 60]

for i in range(0, len(Sensor_samplinginterval)):

    Eload_setup = (14.38 * 60 / (Sensor_samplinginterval[i] * 60) + 60 * Psleep * (1 - 9 / (Sensor_samplinginterval[i] * 60) - 60 / (Communication_interval * 60))) / 3600

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



    fraction_overflow = sum(Overflow) / (sum(Nbat_in * Ncc * Eh) + 0.000000000000001) # Added to avoid div by 0 in case
    print("Percentage overflow: {:.2%}".format(fraction_overflow))

    fraction_sampleloss = np.count_nonzero(Eload == 0) / len(Eload)
    print("Percentage sample loss: {:.2%}".format(fraction_sampleloss))

    Percentage_offTime_list.append(100*fraction_sampleloss)
    Percentage_Joules_overflow_list.append(fraction_overflow)


    print("Simulation "+str(i+1)+" of "+str(len(Sensor_samplinginterval))+" completed.")


fig = plt.figure(figsize=(10, 7), dpi=None, facecolor=None, edgecolor=None, linewidth=1, frameon=True,
                 subplotpars=None)

plt.subplot(2, 1, 1)
plt.plot(Sensor_samplinginterval, Percentage_offTime_list, 's-', color=(0.2, 0.2, 0.2), label='Percentage of Sample Loss')
plt.legend(loc='best', fontsize=20)
plt.tick_params(labelsize=18)
# plt.ylim(-5, 100.01)
# plt.ylim(-0.1, 1)

plt.subplot(2, 1, 2)
plt.plot(Sensor_samplinginterval, Percentage_Joules_overflow_list, 'o-', color=(0.6, 0.6, 0.6), label='Energy Loss Ratio')
plt.xlabel('Sampling Interval [min]', fontsize=20)

plt.ylabel('(a) 04092750 ', fontsize=22)
plt.legend(loc='best', fontsize=20)
plt.tick_params(labelsize=18)
# plt.ylim(-0.05, 0.60)
# plt.ylim(0.39, 1.01)
# plt.show()

plt.savefig('SamplingIntervalEffect_' + '04092750' + ".png", dpi=300)

