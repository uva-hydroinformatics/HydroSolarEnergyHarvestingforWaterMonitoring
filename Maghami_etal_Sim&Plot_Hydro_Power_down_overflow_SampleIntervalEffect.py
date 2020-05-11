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


now = datetime.datetime.now()

df_ = pd.read_csv(os.path.join('./', 'data_files/USGS_Sites_Info_12_7_2019.txt'), encoding="ISO-8859-1", sep='\t',
				  dtype={'site_no': str, 'parm_cd': str, 'huc_cd': str}, usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])

Data_files = ['data_files/hydro_data_files/01103025_72255_UTC.pkl',
			  'data_files/hydro_data_files/02356000_72255_UTC.pkl',
			  'data_files/hydro_data_files/07374525_72255_UTC.pkl']

# Set the y axis limits for plotting
minY_sampleLoss = [-5, -5, -5]
maxY_sampleLoss = [90, 40, 100]
minY_EnergyLoss = [-0.05, -0.05, 0.94]
maxY_EnergyLoss = [1, 1, 1]


Sensor_T_idle = [1, 4, 9, 14, 19, 29, 39, 49, 59]
Sensor_P_active = 18.0/60.0

for i, USGS_site_file in enumerate(Data_files):
	# create empty list to append the filename in the target USGS observation data directory
	Mean_Energy_list = []
	Missing_samples_percent_list = []
	Joules_overflow_ratio_list = []

	for j, T_idle in enumerate(Sensor_T_idle):
		print('\n', '*'*40)
		print(i+1, ' :Reading file: ',  USGS_site_file)
		try:
			# Reads the pickle dataframe
			flow_df = pd.read_pickle(os.path.join('./', USGS_site_file))
		except:
			print("File  could not be found!")  # To be edited

		mask = (flow_df.index >= pd.Timestamp('2010-01-01 00:00:00', tz='GMT'))\
			   & (flow_df.index <= pd.Timestamp('2015-01-01 00:00:00', tz='GMT'))
		flow_df = flow_df.loc[mask]

		# Creates an one-minute linearly interpolated time series
		resampled_flow_df = timeseries.resampledf(flow_df, interp_method='linear', verbose=True)

		# Creates power time series based on first version of water lily turbine model
		power_df = turbine.waterlilyv1(resampled_flow_df, verbose=False)

		# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
		batt = battery.model(1.2, 0.6, verbose=True)

		new_sensor = sensor.model(Sensor_P_active, T_idle, verbose=True)

		# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on (t idle = 0)
		station_controller = controller.model(0, 100, initial_state='active', verbose=True)

		# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
		station_communication = communication.model(0, 100, verbose=True)

		# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
		sensor_station = station.model(station_controller, station_communication, [new_sensor], operation_mode='fixed_battsense', verbose=True)

		# Runs discrete-time simulation
		simulation_output = core.runsim(power_df, sensor_station, batt, verbose = True)

		# Calculate mean harvested energy in 5 minute
		Mean_Energy = simulation_output['generated energy'].mean() * 3600*1000 * 5 # Convert from kwh to J and in a 5-minute window
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
		Joules_overflow_ratio = Total_energy_overflow / (Total_energy + 0.000000000000001)  # Not to div by 0
		Joules_overflow_ratio_list.append(Joules_overflow_ratio)

		print('\nSimulation time so far: ', datetime.datetime.now() - now)
	# np.savetxt('Overflow_.out.txt', [Off_Time, Overflow, Sensor_T_idle], delimiter=',')
	# np.savetxt('Overflow_params_.out.txt', [Sensor_P_active, Battery_capacity, Battery_init_charge], delimiter=',')

	Average_PowerCons = [Sensor_P_active / (x + 1) for x in Sensor_T_idle]

	Sampling_rate = [(1 / (x + 1)) for x in Sensor_T_idle]
	Sampling_time = [(x + 1) for x in Sensor_T_idle]


	fig = plt.figure(figsize=(10, 7), dpi=None, facecolor=None, edgecolor=None, linewidth=1, frameon=True,
					 subplotpars=None)

	plt.subplot(2, 1, 1)
	plt.plot(Sampling_time, Missing_samples_percent_list, 's-', color=(0.2, 0.2, 0.2), label='Percentage of Sample Loss')
	plt.legend(loc='best', fontsize=20)
	plt.tick_params(labelsize=18)
	plt.ylim(minY_sampleLoss[i], maxY_sampleLoss[i])

	plt.subplot(2, 1, 2)
	plt.plot(Sampling_time, Joules_overflow_ratio_list, 'o-', color=(0.6, 0.6, 0.6), label='Energy Loss Ratio')
	plt.xlabel('Sampling Interval [min]', fontsize=20)
	plt.ylabel(USGS_site_file.split("/")[2].split("_")[0], fontsize=22)
	plt.legend(loc='best', fontsize=20)
	plt.tick_params(labelsize=18)
	plt.ylim(minY_EnergyLoss[i], maxY_EnergyLoss[i])

	plt.savefig(os.path.join('./', 'results/SamplingIntervalEffect_' + USGS_site_file.split("/")[2].split("_")[0] + ".png"), dpi=300)

