#################################################################################
#
# Class: model
#
# Description: Controller model class
#
# Attributes:
#				p_active: power consumed in active state (Watts)                                                                                                                 
#				p_idle: power consumed in idle state (Watts) 
#				t_active: time spent on active state (Simulation time steps)
#				t_idle: time spent on idle state (Simulation time steps)
#				timer: stores time steps spent in current state (Simulation time steps)
#				initial_state: controller initial state string for reset ( active or idle)   
#				state: current controller state string ( active or idle)                                                                  
#
# Methods: 
#				getpower: returns power consumption on current state (Watts)
#				getperiod: returns period of current state (minutes)
#             	avgpower: returns communication's average power consumption (Watts)
#
#################################################################################

class model:

    # Controller constructor
	def __init__(self, p_active, t_idle, timer = 1, t_active = 1, p_idle = 0, initial_state = 'idle', verbose = False):
		self.p_active = p_active
		self.t_active = t_active
		self.p_idle = p_idle
		self.t_idle = t_idle
		self.timer = timer

		# Checks if state is valid
		if initial_state == 'active' or initial_state == 'idle':
			self.initial_state = initial_state
			self.state = initial_state
		else:
        	# Raise exception if state is not valid
			raise Exception("Error: "+initial_state+" is not a valid state. Choose either active or idle as initial_state parameter.")

		if verbose == True:
			print(" ")
			print("Controller parameters")
			print("  p_active:      "+"{0:.4f}".format(p_active))
			print("  t_active:      "+"{0:.4f}".format(t_active))
			print("  p_idle:        "+"{0:.4f}".format(p_idle))
			print("  t_idle:        "+"{0:.4f}".format(t_idle))
			print("  initial_state: "+initial_state)
			print(" ")
			print("Controller successfully created!")

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






