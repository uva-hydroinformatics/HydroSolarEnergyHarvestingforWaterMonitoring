#################################################################################
#
# Function: runsim
#
# Description: Runs a discrete time simulation of a self-powered device
#
# Input:    gen_power_df: dataframe containing intantaneous generated power every minute
#			load: station object containing all load components
#			estorage: energy storage device object                                                         
#
# Optional: verbose                                                          
#           
# Output: dataframe containing: timestamp, generated energy, load energy, net energy and battery status
#
# Description: Runs discrete-time simulation and returns a simulation results dataframe 
#
#################################################################################

def runsim(gen_power_df, load, estorage, verbose = False):
	
	# Import library dependencies
	import pandas as pd 
	import numpy as np

	# If verbose is enabled, prints begining of simulation message
	if verbose == True:
		total_sim_steps = gen_power_df.shape[0]
		sim_counter = 0
		print(" ")
		print("starting discrete-time simulation...")
		print("  >number of steps: "+str(total_sim_steps))

	# Creates an empty list to store simulation data
	data = []

	# Runs simulation for every input generated energy value available
	for index, row in gen_power_df.iterrows():

		# Converts generated power to energy (kWh) for 1 minute step 
		gen_energy = row['power']/60000.0

		# Converts consumed power to energy (kWh) for 1 minute step 
		cons_energy = load.getpower()/60000.0

		# Calculates net energy to be stored or consumed
		net_energy = gen_energy - cons_energy
		
		# Stores or consumes net energy from the battery object
		batt_status = estorage.charge(net_energy)

		# Reads total energy stored in the battery
		stored_energy = estorage.stored_energy

		# Checks battery status 
		if batt_status:
			# Updates load states if charging was successfull
			load.updatestate(stored_energy)
		else:
			# Resets load states if charging was not successfull
			load.resetstate()

		# Appends results of simulation step to simulation data list
		data.append({
				'timestamp': 		index,
				'generated energy': gen_energy,
				'load energy':		cons_energy,
				'net energy':		net_energy,
				'stored energy':    stored_energy,
				'battery status':	batt_status
		})

		if verbose == True:
			sim_counter += 1

			if sim_counter == int(0.1*total_sim_steps):
				print("  ... 10 %  done")

			if sim_counter == int(0.5*total_sim_steps):
				print("  ... 50 %  done")

			if sim_counter == int(0.9*total_sim_steps):
				print("  ... 90 %  done")



	# Creates a simulation dataframe
	sim_results_df = pd.DataFrame(data)
	# Selects timestamp as the dataframe index
	sim_results_df.set_index('timestamp',inplace=True)
    # converts timestamp into pandas format 
	sim_results_df.index = pd.to_datetime(sim_results_df.index, utc='true')

	# If verbose is enabled prints simulation results
	if verbose == True:
		print(" ")
		print("Total energy overflow:  "+"{0:.4f}".format(estorage.overflow_energy))
		print("Total powerdown events: "+str(estorage.powerdown_counter))
		print(" ")
		communication_data = load.commdata()
		expected_tx = np.floor(total_sim_steps/communication_data['comm interval'])
		print("Total successfull transmission events: "+str(communication_data['tx count']))
		print("Total successfull reception events   : "+str(communication_data['rx count']))
		print("Communication periodicity:             "+str(communication_data['comm interval']))
		print("Missing transmission ratio:            "+"{0:.4f}".format((expected_tx-communication_data['tx count'])/expected_tx))
		sensor_data = load.sensordata()
		for row in sensor_data:
			expected_samples = np.floor(total_sim_steps/row['sampling interval'])
			print(" ")
			print("Sensor id:                   "+row['sensor id'])
			print("Sensor sampling interval:    "+str(row['sampling interval']))
			print("Total successfull samples:   "+str(row['sample count']))
			if load.op_mode =='fixed' or load.op_mode =='fixed_battsense':
				print("Missing samples ratio:       "+"{0:.4f}".format((expected_samples-row['sample count'])/expected_samples))

	# Returns simulation results data
	return sim_results_df



