# Imports all modules needed for this code
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
import numpy as np
import datetime


now = datetime.datetime.now()

Data_files = []
for file in os.listdir("data_files/hydro_data_files/"):
	if file.endswith(".pkl"):
		Data_files.append(os.path.join("data_files/hydro_data_files/", file))

df_hydro = pd.read_csv(os.path.join('./', 'data_files/USGS_Sites_Info_12_7_2019.txt'), encoding="ISO-8859-1", sep='\t',
					   dtype={'site_no': str, 'parm_cd': str, 'huc_cd': str}, usecols=[0, 1, 2, 3, 4, 5, 6, 9, 10, 11])


# create empty list to append the filename in the target USGS observation data directory
Mean_Energy_list = []
Missing_samples_percent_list = []
Percentage_Joules_overflow_list = []


for i, USGS_site_file in enumerate(Data_files):
	print('\n', '*'*40)
	print(i+1, ' :Reading file: ',  USGS_site_file)
	try:
		# Reads the pickle dataframe
		flow_df = pd.read_pickle(os.path.join('./',USGS_site_file))
	except:
		print("File  could not be found!") # To be edited

	mask = (flow_df.index >= pd.Timestamp('2010-01-01 00:00:00', tz='GMT')) & \
		   (flow_df.index <= pd.Timestamp('2015-01-01 00:00:00', tz='GMT'))
	flow_df = flow_df.loc[mask]

	# Creates an one-minute linearly interpolated time series
	resampled_flow_df = timeseries.resampledf(flow_df, interp_method='linear', verbose=True)

	# Creates power time series based on first version of water lily turbine model
	power_df = turbine.waterlilyv1(resampled_flow_df, verbose=False)

	# Creates a battery model object with capacity of 1.2 kWh and 0.6 kWh initial charge
	batt = battery.model(1.2, 0.6, verbose=True)

	new_sensor = sensor.model(18.0/(60.0), 4, verbose=True)

	# Creates a controller model with active power consumption of 0.5 Watts, initial state active and always on
	# (t idle = 0)
	station_controller = controller.model(0, 100, initial_state='active', verbose=True)

	# Creates a communication's module model with active power consumption of 5 watts and idle period of 59 minutes
	station_communication = communication.model(0, 100, verbose=True)

	# # Creates a sensor station operating in 'fixed' mode with all previously created load objects
	sensor_station = station.model(station_controller, station_communication, [new_sensor],
								   operation_mode='fixed_battsense', verbose=True)

	# Runs discrete-time simulation
	simulation_output = core.runsim(power_df, sensor_station, batt, verbose = True)

	# Calculate mean harvested energy in 5 minute
	Mean_Energy = simulation_output['generated energy'].mean() * 3600*1000 * 5 # Convert from kwh to J and in a 5-minute
	# window
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
	Percentage_Joules_overflow = 100 * Total_energy_overflow / (Total_energy + 0.000000000000001)  # Add not to div by 0
	Percentage_Joules_overflow_list.append(Percentage_Joules_overflow)

	print('\nSimulation time so far: ', datetime.datetime.now() - now)


df_hydro['MeanEnergy_Hydro'] = Mean_Energy_list  # in 5 minutes
df_hydro['PerOfftime_Hydro'] = Missing_samples_percent_list
df_hydro['PerjoulOvFl_Hydro'] = Percentage_Joules_overflow_list

df_hydro.to_csv(os.path.join('./', 'results/Hydro_Simulation.csv'), sep=',')


