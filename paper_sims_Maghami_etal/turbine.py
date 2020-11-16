#################################################################################
#
# Function: generictf
#
# Description: Generates a generic transfer function for a turbine and creates a
#			   instantaneous power time series from input data
#
# Input:    flow_df
#			min_flow
#			max_flow
#			radius
#			efficiency
#
# Optional: flow_unit
#			fluid_density
#           verbose
#			enable_plot
#
# Output: returns generated power time series as a pandas data frame
#
#################################################################################

def generictf(flow_df, min_flow, max_flow, radius, efficiency, flow_unit='feet/sec', fluid_density=1000, verbose=False, enable_plot=False):

	# Turbine's flow velocity to power transfer curve model
	def transferfunction(flow, flow_unit, min_flow, max_flow, radius, efficiency, fluid_density):

		# Checks if flow velocity units are valid and perform conversion
		if flow_unit=='feet/sec':
			# Converts the flow velocity from feet/s to meters/s
			v_ms=abs(flow)*0.3048
			max_v_ms=abs(max_flow)*0.3048

		else:
			if flow_unit=='meters/sec':
				# Stores the flow velocity in meters/s
				v_ms=abs(flow)
				max_v_ms=abs(max_flow)

			else:
				# If flow unit is not feet/sec nor meters/sec
				raise NameError("Error: flow velocity unit "+flow_unit+" is not currently supported")

		# Checks if flow velocity is above minimum value to generate power
		if abs(flow)>(min_flow):

			# Checks if flow velocity is bellow maximum value (output is not yet saturated)
			if abs(flow)<(max_flow):
				# Returns power calculated from transfer function considering incompressible fluid
				return (efficiency*(fluid_density)*3.14159*(radius**2)*(v_ms**3))/2

			else:
				# Returns saturated max power
				return (efficiency*(fluid_density)*3.14159*(radius**2)*(max_v_ms**3))/2
		else:

			# Returns zero power
			return 0


	# Imports library dependencies
	import pandas as pd
	import matplotlib.pyplot as plt

	# Checks if verbose is true and prints input parameters for calculation
	if verbose==True:
		print(" ")
		print("The input turbine parameters to calculate instantaneous power generation are:")
		print("  Min flow velocity: "+str(min_flow)+" in "+flow_unit)
		print("  Max flow velocity: "+str(max_flow)+" in "+flow_unit)
		print("  Radius:            "+str(radius)+" in meters")
		print("  Efficiency:        "+str(efficiency))
		print(" ")
		print("Fluid density is "+str(fluid_density)+" kg per cubic meter")

		# Display warning for high efficiency values
		if efficiency>0.593:
			print(" ")
			print("Warning: Efficiency is above Betz Limit (0.593)")

		# Checks if enable_plot is true and plots turbine's transfer function
		if enable_plot==True:
			# Plots the transfer function of selected turbine model
			flow = [0.01*x for x in range(0, int(110*max_flow))]
			power = [transferfunction(x, flow_unit, min_flow, max_flow, radius, efficiency, fluid_density) for x in flow]
			plt.plot(flow,power)
			plt.title("Flow Velocity to Power Transfer Curve")
			plt.xlabel("Flow velocity in "+flow_unit)
			plt.ylabel("Output power in Watts")
			plt.show()
			#plt.grid(b=True)
			#plt.draw()
			#plt.pause(3)
			#plt.figure()

	# Creates power time series as an empty dataframe
	power_df = pd.DataFrame()

	# Converts flow velocity time series in instantaneous power time series
	power_df['power'] = flow_df.flow.apply(lambda x: transferfunction(x, flow_unit, min_flow, max_flow, radius, efficiency, fluid_density))

	# Checks if verbose is true and prints average power generation
	if verbose==True:
		print(" ")
		print("Average power generation: "+"{0:.4f}".format(power_df['power'].mean())+" Watts")

	# Returns generated power dataframe
	return power_df



#################################################################################
#
# Function: waterlilyv1
#
# Description: First version of the Water Lily turbine transfer function
#
# Input:   flow_df
#
# Optional: flow_unit,
#			fluid_density,
#           verbose
#			enable_plot
#
# Output: returns generated power time series as a pandas data frame
#
#################################################################################

def waterlilyv1(flow_df, flow_unit='feet/sec', fluid_density=1000, verbose=False, enable_plot=False):

	# Imports library dependencies
	import pandas as pd

	# Turbine parameters
	radius = 0.09 # in meters (D = 180 mm)
	efficiency = 0.27815 # estimated to fit transfer function plot

	if flow_unit=='feet/sec':
		# Turbine parameters
		min_flow = 0.9113 # in feet per second (1 Km/h)
		max_flow = 5.2858 # in feet per second (5.8 Km/h)
	else:
		if flow_unit=='meters/sec':
			# Turbine parameters
			min_flow = 0.2778 # in meters per second (1 Km/h)
			max_flow = 1.6111 # in meters per second (5.8 Km/h)
		else:
			# If flow unit is not feet/sec nor meters/sec
			raise NameError("Error: flow velocity unit "+flow_unit+" is not currently supported")


	# Converts flow velocity time series into instantaneous power time series using generic turbine function
	power_df = generictf(flow_df, min_flow, max_flow, radius, efficiency, flow_unit=flow_unit, fluid_density=fluid_density, verbose=verbose, enable_plot=enable_plot)

	return power_df



#################################################################################
#
# Function: waterlilyv2
#
# Description: Second version of the Water Lily turbine transfer function
#
# Input:   flow_df
#
# Optional: flow_unit,
#			fluid_density,
#           verbose
#
# Output: returns generated power time series as a pandas data frame
#
#################################################################################

def waterlilyv2(flow_df, flow_unit='feet/sec', fluid_density=1000, verbose=False, enable_plot=False):

    # Water Lily turbine's flow velocity to power transfer curve model based on manufacturer's plot
	def transferfunction2(flow, flow_unit, min_flow, max_flow, fluid_density):

		# Checks if flow velocity units are valid and perform conversion
		if flow_unit=='feet/sec':
			# Converts the flow velocity from feet/s to meters/s
			v_kmh=abs(flow)*1.09728
			max_v_kmh=abs(max_flow)*1.09728

		else:
			if flow_unit=='meters/sec':
				# Stores the flow velocity in meters/s
				v_kmh=abs(flow)*3.6
				max_v_kmh=abs(max_flow)*3.6

			else:
				# If flow unit is not feet/sec nor meters/sec
				raise NameError("Error: flow velocity unit "+flow_unit+" is not currently supported")

		# Checks if flow velocity is above minimum value to generate power
		if abs(flow)>(min_flow):

			# Checks if flow velocity is bellow maximum value (output is not yet saturated)
			if abs(flow)<(max_flow):
				# Returns power calculated from transfer function considering proportionality to fluid density
				return (fluid_density/1000)*(0.1056*(v_kmh**2)+0.0669*(v_kmh)-0.4709)

			else:
				# Returns saturated max power
				return (fluid_density/1000)*(0.1056*(max_v_kmh**2)+0.0669*(max_v_kmh)-0.4709)
		else:

			# Returns zero power
			return 0


	# Imports library dependencies
	import pandas as pd
	import matplotlib.pyplot as plt


	if flow_unit=='feet/sec':
		# Turbine parameters
		min_flow = 1.6586 # in feet per second (1.82 Km/h)
		max_flow = 10.4804 # in feet per second (11.5 Km/h)
	else:
		if flow_unit=='meters/sec':
			# Turbine parameters
			min_flow = 0.5056 # in meters per second (1.82 Km/h)
			max_flow = 3.1944 # in meters per second (11.5 Km/h)
		else:
			# If flow unit is not feet/sec nor meters/sec
			raise NameError("Error: flow velocity unit "+flow_unit+" is not currently supported")

	# Checks if verbose is true and prints input parameters for calculation
	if verbose==True:
		print(" ")
		print("The input turbine parameters to calculate instantaneous power generation are:")
		print("  Min flow velocity: "+str(min_flow)+" in "+flow_unit)
		print("  Max flow velocity: "+str(max_flow)+" in "+flow_unit)
		print("  Transfer equation: P = 0.1056*(v_kmh^2) + 0.0669*(v_kmh) - 0.4709 in Watts")
		print(" ")
		print("Fluid density is "+str(fluid_density)+" kg per cubic meter")

		# Checks if enable_plot is true and plots turbine's transfer function
		if enable_plot==True:
			flow = [0.01*x for x in range(0, int(110*max_flow))]
			power = [transferfunction2(x, flow_unit, min_flow, max_flow, fluid_density) for x in flow]
			plt.plot(flow,power)
			plt.title("Flow Velocity to Power Transfer Curve")
			plt.xlabel("Flow velocity in "+flow_unit)
			plt.ylabel("Output power in Watts")
			#plt.grid(b=True)
			plt.show()

	# Creates power time series as an empty dataframe
	power_df = pd.DataFrame()

	# Converts flow velocity time series in instantaneous power time series
	power_df['power'] = flow_df.flow.apply(lambda x: transferfunction2(x, flow_unit, min_flow, max_flow, fluid_density))

	# Checks if verbose is true and prints average power generation
	if verbose==True:
		print(" ")
		print("Average power generation: "+"{0:.4f}".format(power_df['power'].mean())+" Watts")

	# Returns generated power dataframe
	return power_df