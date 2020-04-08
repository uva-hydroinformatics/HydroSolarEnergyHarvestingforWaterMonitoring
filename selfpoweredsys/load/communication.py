#################################################################################
#
# Class: model
#
# Description: Communication model class
#
# Attributes:
#               p_tx: power consumed in transmitting state (Watts) 
#				t_tx: time spent in transmitting state
#				p_rx: power consumed in receiving state (Watts) 
#				t_rx: time spent in receiving state  
#				p_sleep: power consumed in sleeping state (Watts) 
#				t_sleep: time spent in sleeping state 
#				timer: stores time steps spent in current state (Simulation time steps) 
#				tx_count: number of successfull tranmitting events
#				rx_count: number of successfull receiving events
#				initial_state: comm module initial state string for reset ( active or idle)   
#				state: current comm module state string ( active or idle)   
#				valid_states: list of valid states ['sleep', 'receiving', 'transmitting']
#
# Methods: 
#				getpower: returns power consumption on current state
#				getperiod: returns period of current state
#             	avgpower: returns communication's average power consumption
#
#################################################################################

class model:

    # Communications constructor
	def __init__(self, p_tx, t_sleep, timer = 1, p_rx = 0, t_tx = 1, t_rx = 0,  p_sleep = 0, initial_state = 'sleep', verbose = False):
		self.p_tx = p_tx
		self.t_tx = t_tx
		self.p_rx = p_rx
		self.t_rx = t_rx
		self.p_sleep = p_sleep
		self.t_sleep = t_sleep
		self.timer = timer
		self.tx_count = 0
		self.rx_count = 0
		self.valid_states = ['sleep', 'receiving', 'transmitting']

        # Checks if state is valid
		if initial_state in self.valid_states:
			self.initial_state = initial_state
			self.state = initial_state
		else:
        	# Raise exception if state is not valid
			raise Exception("Error: "+initial_state+" is not a valid state. Choose one of the following states:"+self.valid_states)

		# Checks if verbose is enabled and prints communication module parameters
		if verbose == True:
			print(" ")
			print("Communications module parameters")
			print("  p_tx:          "+"{0:.4f}".format(p_tx))
			print("  t_tx:          "+"{0:.4f}".format(t_tx))
			print("  p_rx:          "+"{0:.4f}".format(p_rx))
			print("  t_rx:          "+"{0:.4f}".format(t_rx))
			print("  p_sleep:       "+"{0:.4f}".format(p_sleep))
			print("  t_sleep:       "+"{0:.4f}".format(t_sleep))
			print("  initial_state: "+initial_state)
			print(" ")
			print("Communications module successfully created!")

    # Returns the power consumption of current state
	def getpower(self):
		return {
				'sleep': self.p_sleep,
				'receiving': self.p_rx,
				'transmitting': self.p_tx
				}.get(self.state, None)

	# Returns the period of current state
	def getperiod(self):
		return {
				'sleep': self.t_sleep,
				'receiving': self.t_rx,
				'transmitting': self.t_tx
				}.get(self.state, None)

    # Communication's average power consumption
	def avgpower(self):
    	# Calculates average power consumption
		return ((self.p_tx*self.t_tx + self.p_rx*self.t_rx + self.p_sleep*self.t_sleep)/(self.t_tx + self.t_rx + self.t_sleep))

