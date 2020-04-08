#################################################################################
#
# Function: eneutralreq
#
# Description: Calculates initial charge and storage capacity for energy neutral operation
#			   considering ideal battery
#
# Input:    power_df
#                                                         
#
# Optional: verbose                                                          
#           
#
# Output: 	Returns energy storage capacity (kWh) and initial charge (kWh) to achieve energy
#			neutral operation with ideal energy buffer. Also returns mean power (Watts) and 
#			total energy (kWh) for power dataframe given as input.
#
#################################################################################

def eneutralreq(power_df, verbose=False):

	# Imports the library dependencies
	import pandas as pd 

	# Calculates the mean value of the input power time series
	mean_power = power_df['power'].mean()

	# Calculates total energy in kwh, assuming sampling interval of one minute
	total_energy_kwh = power_df['power'].sum()/60000

	# Checks if verbose is enabled and output input data information
	if verbose==True:
		print(" ") 
		print("Input power dataframe:")
		print(power_df.head())
		print(" ") 
		print("Input power information")
		print("  Mean power generated in this window (Watts): "+"{0:.4f}".format(mean_power))
		print("  Energy generated in this window (kWh):       "+"{0:.4f}".format(total_energy_kwh))

	# Creates net energy (kWh) time series as an empty dataframe
	net_energy_kwh = pd.DataFrame()

	# Calculates net energy being stored or consumed on a battery 
	net_energy_kwh['energy'] = power_df['power'].apply(lambda x: (x-mean_power)/60000.0).cumsum()

	# Calculates maximum surplus and deficit in the battery
	max_surplus_kwh = net_energy_kwh['energy'].max()
	max_deficit_kwh = net_energy_kwh['energy'].min()

	# Verify if surplus is negative and limits it to zero
	if max_surplus_kwh < 0:
		max_surplus_kwh = 0

	# Verify if deficit is negative and limits it to zero
	if max_deficit_kwh > 0:
		max_deficit_kwh = 0

	# Calculates total battery capacity to achieve energy neutral operation
	batt_capacity = max_surplus_kwh + abs(max_deficit_kwh)

	# Calculates initial charge to achieve energy neutral operation
	initial_charge = abs(max_deficit_kwh)

	# Checks if verbose is enabled and output results
	if verbose==True:
		print(" ")        
		print("Battery requirements for energy neutral operation: ")
		print("  Battery capacity (kWh): 	"+"{0:.4f}".format(batt_capacity))
		print("  Initial charge (kWh):      "+"{0:.4f}".format(initial_charge))
		if batt_capacity>0:
			print("  Initial charge percentage: "+"{0:.2f}".format(100*(initial_charge/batt_capacity))+"%")

	return [batt_capacity, initial_charge, mean_power, total_energy_kwh, net_energy_kwh]	



#################################################################################
#
# Class: model
#
# Brief description: Battery model class
#
# Attributes:   max_capacity                                                           
#               stored_energy                                                         
#               leakage
#			    charging_efficiency
#				discharging_efficiency
#
#				charging_cycles_count
#				charging_cycles_value
#				discharging_cycles_count
#				discharging_cycles_value
#				overflow_energy
#				powerdown_counter
#                                                       
# Methods: 	    charge()
#
# Description:  Models a battery object, with given max capacity and initial charge.
#			    Object parameters include constant leakage and both charging and 
#				discharging efficiencies.
#				Internal states are: stored energy; overflow energy (amount of energy
#				that the battery could not store due to capacity limit); power down 
#				counter; charging and discharging cycles and total value.
#				charge(energy) method updates the stored energy based on efficiencies
#				and net charge or discharge energy value (discharges are negative 
#				energies).
#				This object is agnostic to the energy unit adopted, but kWh is 
#				recommended since many battery specifications use this unit.
#
#
#################################################################################

class model:

	# Battery constructor with default attributes
	def __init__(self, max_capacity, initial_charge, charging_efficiency = 1, discharging_efficiency = 1, leakage = 0, verbose=False):
		self.max_capacity = max_capacity 						# Max battery capacity (same unit as charge function input)
		self.stored_energy = initial_charge						# Stored energy        (same unit as charge function input)
		self.leakage = leakage				    				# Battery leakage (same unit as charge function input)
		self.charging_efficiency = charging_efficiency			# Efficiency in charging operation (0 to 1)
		self.discharging_efficiency = discharging_efficiency	# Efficiency in discharging operation (0 to 1)
		
		# Battery usage state variables:
		self.charging_cycles_count = 0			# Charging cycle count
		self.charging_cycles_value = 0			# Charging cycle accumulated value
		self.discharging_cycles_count = 0		# Discharging cycle count
		self.discharging_cycles_value = 0		# Discharging cycle accumulated value
		self.overflow_energy = 0				# Wasted energy due to overflow
		self.powerdown_counter = 0				# Power down counter

		# If verbose is enabled, prints sensor parameters
		if verbose == True:
			print(" ")
			print("Battery parameters")
			print("  max_capacity:           "+"{0:.4f}".format(max_capacity))
			print("  initial_charge:         "+"{0:.4f}".format(initial_charge))
			print("  leakage:                "+"{0:.4f}".format(leakage))
			print("  charging_efficiency:    "+"{0:.4f}".format(charging_efficiency))
			print("  discharging_efficiency: "+"{0:.4f}".format(discharging_efficiency))
			print(" ")
			print("Battery successfully created!")

	# def __del__(self):
	# 	print("battery model deleted")

	# Updates stored energy by charging or discharging the amount of energy used as input 
	def charge(self, energy):

		# Checks if it is a charging or discharging operation
		if energy>0:

			# Calculates the amount of charge added to storage
			charge_value = self.charging_efficiency*energy - self.leakage

			# Checks if the storage achieves maximum capacity
			if self.max_capacity - charge_value - self.stored_energy > 0:

				# Updates the stored energy in the battery, total charging value and cycle count
				self.stored_energy += charge_value
				self.charging_cycles_value += charge_value
				self.charging_cycles_count += 1

				# Returns true for successful operation
				return True

			else:

				# Updates the stored energy in the battery, overflow, total charging value and cycle count
				self.charging_cycles_value += self.max_capacity - self.stored_energy
				self.charging_cycles_count += 1
				self.overflow_energy += self.stored_energy + charge_value - self.max_capacity
				self.stored_energy = self.max_capacity


				# Returns true for successful operation
				return True

		else:

			# Calculates the amount of charge drained from storage
			charge_value = (1/self.discharging_efficiency)*energy - self.leakage

			# Checks if the storage runs out of power
			if charge_value + self.stored_energy > 0:

				# Updates the stored energy in the battery, total discharging value and cycle count
				self.stored_energy += charge_value 
				self.discharging_cycles_value += charge_value
				self.discharging_cycles_count += 1

				# Returns true for successful operation
				return True

			else:

				# Updates the stored energy in the battery, total discharging value and cycle count
				self.discharging_cycles_value += self.stored_energy
				self.discharging_cycles_count += 1
				self.stored_energy = 0
				self.powerdown_counter += 1

				# Returns false for unsuccessful operation (power down)
				return False


