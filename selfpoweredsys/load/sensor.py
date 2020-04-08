#################################################################################
#
# Class: model
#
# Brief description: Sensor model class
#
# Attributes:
#				p_active: power consumed in active state (Watts)                                                                                                                 
#				p_idle: power consumed in idle state (Watts) 
#				t_active: time spent on active state (Simulation time steps)
#				t_idle: time spent on idle state (Simulation time steps)
#				timer: stores time steps spent in current state (Simulation time steps)
#				sensor_id: stores sensor name in a string
#				sample_count: counter of succesfull samples
#				initial_state: sensor initial state string for reset ( active or idle)   
#				state: current sensor state string ( active or idle)                                                         
#
# Methods: 		getpower: returns power consumption on current state (Watts)
#				getperiod: returns period of current state (Simulation time steps)
#             	avgpower: returns communication's average power consumption (Watts)
#
# Description:  Models a sensor device with two states: "active" and "idle".
#				Internal variable sample_count stores the number of successfull samples.
#
#
#################################################################################

class model:

    # Sensor constructor
	def __init__(self, p_active, t_idle, timer = 1, t_active = 1, p_idle = 0, initial_state = 'idle', sensor_id = 'sensor', verbose = False):
		self.p_active = p_active
		self.t_active = t_active
		self.p_idle = p_idle
		self.t_idle = t_idle
		self.timer = timer
		self.sensor_id = sensor_id
		self.sample_count = 0

		# Checks if state is valid and load values in object attributes
		if initial_state == 'active' or initial_state == 'idle':
			self.initial_state = initial_state
			self.state = initial_state
		else:
        	# Raise exception if state is not valid
			raise Exception("Error: "+initial_state+" is not a valid state. Choose either active or idle as initial_state parameter.")

		# If verbose is enabled, prints sensor parameters
		if verbose == True:
			print(" ")
			print("Sensor parameters")
			print("  sensor_id:     "+sensor_id)
			print("  p_active:      "+"{0:.4f}".format(p_active))
			print("  t_active:      "+"{0:.4f}".format(t_active))
			print("  p_idle:        "+"{0:.4f}".format(p_idle))
			print("  t_idle:        "+"{0:.4f}".format(t_idle))
			print("  initial_state: "+initial_state)
			print(" ")
			print("Sensor successfully created!")

    # Returns the power consumption of current state
	def getpower(self):
		return {
				'active': self.p_active,
				'idle': self.p_idle,
				}.get(self.state, None)

	# Returns the period of current state
	def getperiod(self):
		return {
				'active': self.t_active,
				'idle': self.t_idle,
				}.get(self.state, None)

    # Sensor's average power consumption
	def avgpower(self):
    	# Calculates average power consumption by idle and active periods
		return ((self.p_active*self.t_active + self.p_idle*self.t_idle)/(self.t_active+self.t_idle))



#################################################################################
#
# Function: calc_avg_pactive
#
# Description: Calculates the average active power in one simulation time step
#
# Input:    voltage:  sensor's voltage in Volts
#			current:  sensor's current in Amperes
#			t_warmup: sensor's warm up time in seconds
#			t_sensing: sensor's sensing time in seconds
#			t_total: sensor's total time in seconds to perform average
#                                                            
# Output: returns average active power for given total time 
#
#################################################################################

def calc_avg_pactive(voltage, current, t_warmup, t_sensing, t_total):
	# Calculates the average p_active in one simulation step considering warm up time and sensing time
	return((voltage*current)*((t_warmup+t_sensing)/t_total))



#################################################################################
#
# Function: global_wq_sensors
#
# Description: 
#
# Input:  sensor_voltage: sensor's voltage in Volts
#		  t_sensing: time spent sensing in seconds
#		  t_step: simulation step in seconds  
#		  t_active: time spent in active mode in minutes
#		  'sensor code' = sampling interval in minutes
#
# Valid Sensor codes: WQ101, WQ401, WQ730, WQ301, WQ201, WQ600, WQ-COND, WQ-FDO
#
# Example of use case: global_wq_sensors(WQ101=30, WQ201=60)
#						
# Output: returns sensor objects for the input list of global water quality sensors 
#
#################################################################################

def global_wq_sensors(verbose = False, sensor_voltage=12, t_sensing=1, t_step=60, t_active=1,**sensor_list):

	# Initializes water quality sensors list
	wq_sensors = []

	# For every sensor used as input, create sensor object
	for sensor in sensor_list:

		# Checks if verbose is enabled and outputs sensor code
		if verbose == True:
			print(" ")
			print("Creating sensor "+sensor+"...")

		# Get input sampling interval for sensor
		sampling_interval = sensor_list.get(sensor)

		# Load warm up time and maximum current for each sensor
		[t_warmup, max_current] = {
	        'WQ101': [5, 19 *10**-3],
	        'WQ401': [10, 30.8 *10**-3],
	        'WQ730': [8, 60 *10**-3],
	        'WQ301': [3, 25.5 *10**-3],
	        'WQ201': [3, 35.6 *10**-3],
	        'WQ600': [3, 32.5 *10**-3],
	        'WQ-COND': [15, 60 *10**-3],
	        'WQ-FDO': [8, 65 *10**-3]
	    }.get(sensor, [None, None])

	    # Raise exception if sensor code is not in the list
		if t_warmup == None:
	    	# Raise exception if sensor code is not valid
			raise Exception("Error: "+sensor+" is not a valid sensor code. Check sensor.py script for the list of valid sensor codes.")

	    # Calculates idle time based on sampling interval and active time
		t_idle = sampling_interval - t_active

	    # Calculates average p_active assuming the sensor only stays on for input sensing time after warm up
		p_active = calc_avg_pactive(sensor_voltage, max_current, t_warmup, t_sensing, t_step)

	    # Appends each sensor to the list
		wq_sensors.append(model(p_active, t_idle,sensor_id = sensor , verbose = True))

	# Outputs sensor object list
	return wq_sensors
