#################################################################################
#
# Class: model
#
# Description: Station model class
#
# Attributes:  controller: object representing the controller power consumption
#              communication: object representing the communications module power consumption
#              sensors: collection of objects representing each sensor power consumption
#
#              verbose: enables text output for this simulation
#              operation_mode: defines how station should operate its load 
#              operation_parameters: defines the list of parameters for the operation mode
#
#              sensors_ref_t_idle: reference value of sensors t idle to perform duty-cycle 
#              contr_ref_t_idle: reference value of controller t idle to perform duty-cycle 
#              comm_ref_t_sleep: reference value of communication t sleep to perform duty-cycle 
#
# Methods:     getpower: returns power consumption on current state (Watts) for all loads
#              avgpower: returns communication's average power consumption (Watts) for all loads
#              sensordata: return sensor id, sample count and sampling interval for all sensor components
#              commdata: returns tx_count, rx_count and communication interval
#              resetstate: updates all load states to initial states
#              updatestate: updates the state of each load component following selected operation mode
#
# Description: Models a colection of load objects: a set of sensors, a controller and a communications 
#              module. This model defines the operation mode logic of the load components.
#               
#
#################################################################################

class model:
    
    # Station constructor with default attributes
    def __init__(self, controller, communication, sensors, verbose = False, operation_mode = 'fixed', **operation_parameters):
        self.sensors = sensors
        self.controller = controller
        self.communication = communication
        self.op_mode = operation_mode
        self.op_params = operation_parameters

        # stores reference t idle for duty-cycling
        self.sensors_ref_t_idle = []
        for sensor in sensors:
            self.sensors_ref_t_idle.append(sensor.t_idle)
        self.contr_ref_t_idle = self.controller.t_idle
        self.comm_ref_t_sleep = self.communication.t_sleep

        # If verbose is enabled, prints sensor parameters
        if verbose == True:
            print(" ")
            print("Sensing station parameters")
            print("  average power consumption: "+"{0:.4f}".format(self.avgpower()))
            print("  operation mode:            "+self.op_mode)
            print(" ")
            print("Sensor station successfully created!")

    # Returns the power consumption of current state
    def getpower(self):
        # Total power is the sum of each component power output
        total_power = 0
        for sensor in self.sensors:
            total_power += sensor.getpower()
        
        total_power += self.controller.getpower()
        total_power += self.communication.getpower()

        # Returns power consumption for all components
        return total_power

    # Station's average power consumption
    def avgpower(self):
        # Average power is the sum of the average power of components
        total_avgpower = 0
        for sensor in self.sensors:
            total_avgpower += sensor.avgpower()
        
        total_avgpower += self.controller.avgpower()
        total_avgpower += self.communication.avgpower()
        # Returns average power consumption for all components
        return total_avgpower

    # Reads sensor's id and sample count 
    def sensordata(self):
        # Creates an empty list
        sensor_data = []

        # Reads each sensor's id and sample count
        for sensor in self.sensors:
            # Stores info in sensor data list
            sensor_data.append({
                'sensor id':            sensor.sensor_id,
                'sample count':         sensor.sample_count,
                'sampling interval':    (sensor.t_idle+sensor.t_active)
            })

        # Returns sensor data
        return sensor_data

    # Reads communication's module data 
    def commdata(self):
        # Creates communication module's data variable
        comm_data = {
                'tx count':         self.communication.tx_count,
                'rx count':         self.communication.rx_count,
                'comm interval':    (self.communication.t_sleep+self.communication.t_rx+self.communication.t_tx)
            }

        # Returns communication's data
        return comm_data


    # Resets component's state 
    def resetstate(self):
        # Resets each sensor's state
        for sensor in self.sensors:
            sensor.state = sensor.initial_state
            sensor.timer = 1
        # Resets controller's state
        self.controller.state = self.controller.initial_state
        self.controller.timer = 1

        # Resets communication's state
        self.communication.state = self.communication.initial_state
        self.communication.timer = 1


    # Update component's state 
    def updatestate(self, stored_energy):

        ##############################################################################
        #
        # Mode:         Fixed Sampling Interval 
        #
        # Description:  This operation mode activate loads at a fixed time interval 
        #               without checking battery status
        #
        ##############################################################################     
        if self.op_mode == 'fixed':

            # Updates controller's state
            if self.controller.t_idle == 0:
                self.controller.state = 'active'
            else:
                if self.controller.state == 'idle':
                    if self.controller.timer < self.controller.t_idle:
                        self.controller.timer += 1
                    else:
                        self.controller.timer = 1
                        self.controller.state = 'active'
                else:        
                    if self.controller.state == 'active':
                        if self.controller.timer < self.controller.t_active:
                            self.controller.timer += 1
                        else:
                            self.controller.timer = 1
                            self.controller.state = 'idle'

            # Updates each sensor's state
            for sensor in self.sensors:
                if sensor.t_idle == 0:
                    sensor.state = 'active'
                    sensor.sample_count += 1
                else:
                    if sensor.state == 'idle':
                        if sensor.timer < sensor.t_idle:
                            sensor.timer += 1
                        else:
                            sensor.timer = 1
                            sensor.state = 'active'
                    else:        
                        if sensor.state == 'active':
                            if sensor.timer < sensor.t_active:
                                sensor.timer += 1
                            else:
                                sensor.timer = 1
                                sensor.sample_count += 1
                                sensor.state = 'idle'

            # Updates communication's state
            if self.communication.t_sleep == 0 and self.communication.t_rx == 0:
                self.communication.state = 'transmitting'
                self.communication.tx_count += 1
            else:
                if self.communication.state == 'sleep':
                        if self.communication.timer < self.communication.t_sleep:
                            self.communication.timer += 1
                        else:
                            self.communication.timer = 1
                            self.communication.state = 'transmitting' 
                else:
                    if self.communication.state == 'transmitting':
                            if self.communication.timer < self.communication.t_tx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.tx_count += 1
                                if self.communication.t_rx == 0:
                                    self.communication.state = 'sleep'
                                else:
                                    self.communication.state = 'receiving'
                    else:
                        if self.communication.state == 'receiving':
                            if self.communication.timer < self.communication.t_rx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.rx_count += 1
                                self.communication.state = 'sleep'

        ##############################################################################
        #
        # Mode:         Fixed Sampling Interval With Battery Status Sense
        #
        # Description:  This operation mode activate loads at a fixed time interval 
        #               and before turning on sensor and communication devices, it
        #               checks if there is enough stored energy to perform load's 
        #               operation (sampling or communication)
        #
        ##############################################################################                               
        if self.op_mode == 'fixed_battsense':

            # Updates controller's state
            if self.controller.t_idle == 0:
                self.controller.state = 'active'
            else:
                if self.controller.state == 'idle':
                    if self.controller.timer < self.controller.t_idle:
                        self.controller.timer += 1
                    else:
                        self.controller.timer = 1
                        self.controller.state = 'active'
                else:        
                    if self.controller.state == 'active':
                        if self.controller.timer < self.controller.t_active:
                            self.controller.timer += 1
                        else:
                            self.controller.timer = 1
                            self.controller.state = 'idle'

            # Updates each sensor's state
            for sensor in self.sensors:
                if sensor.t_idle == 0:
                    sensor.state = 'active'
                    sensor.sample_count += 1
                else:
                    if sensor.state == 'idle':
                        if sensor.timer < sensor.t_idle:
                            sensor.timer += 1
                        else:
                            if stored_energy > (sensor.p_active*sensor.t_active)/60000.0:
                                sensor.timer = 1
                                sensor.state = 'active'
                    else:        
                        if sensor.state == 'active':
                            if sensor.timer < sensor.t_active:
                                sensor.timer += 1
                            else:
                                sensor.timer = 1
                                sensor.sample_count += 1
                                sensor.state = 'idle'

            # Updates communication's state
            if self.communication.t_sleep == 0 and self.communication.t_rx == 0:
                self.communication.state = 'transmitting'
                self.communication.tx_count += 1
            else:
                if self.communication.state == 'sleep':
                        if self.communication.timer < self.communication.t_sleep:
                            self.communication.timer += 1
                        else:
                            if stored_energy > (self.communication.p_tx*self.communication.t_tx)/60000.0:
                                self.communication.timer = 1
                                self.communication.state = 'transmitting' 
                else:
                    if self.communication.state == 'transmitting':
                            if self.communication.timer < self.communication.t_tx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.tx_count += 1
                                if self.communication.t_rx == 0:
                                    self.communication.state = 'sleep'
                                else:
                                    self.communication.state = 'receiving'
                    else:
                        if self.communication.state == 'receiving':
                            if self.communication.timer < self.communication.t_rx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.rx_count += 1
                                self.communication.state = 'sleep'

        ##############################################################################
        #
        # Mode:         Stoplight With Two Modes
        #
        # Description:  This operation mode alternates sampling interval between two
        #               options, the regular operation for battery above a given
        #               energy threshold and a low power operation with increased duty
        #               cycle factor 
        #
        ##############################################################################     
        if self.op_mode == 'stoplight2':

            # Updates controller's state
            if self.controller.t_idle == 0:
                self.controller.state = 'active'
                # Loads operation mode parameters
                energy_threshold = self.op_params.get('energy_threshold')
                duty_cycle_factor = self.op_params.get('duty_cycle_factor') 

                # Checks if stored energy in the battery and updates duty cycle of loads
                if stored_energy < energy_threshold:
                    i = 0
                    # Updates each sensor's t idle
                    for sensor in self.sensors:
                        sensor.t_idle = duty_cycle_factor*self.sensors_ref_t_idle[i]
                        i += 1
                    # Updates controller's t idle
                    self.controller.t_idle = duty_cycle_factor*self.contr_ref_t_idle
                    # Updates communication's t sleep
                    self.communication.t_sleep = duty_cycle_factor*self.comm_ref_t_sleep         
                else:
                    i = 0
                    # Updates each sensor's t idle
                    for sensor in self.sensors:
                        sensor.t_idle = self.sensors_ref_t_idle[i]
                        i += 1
                    # Updates controller's t idle
                    self.controller.t_idle = self.contr_ref_t_idle
                    # Updates communication's t sleep
                    self.communication.t_sleep = self.comm_ref_t_sleep 
            else:
                if self.controller.state == 'idle':
                    if self.controller.timer < self.controller.t_idle:
                        self.controller.timer += 1
                    else:
                        self.controller.timer = 1
                        self.controller.state = 'active'
                else:        
                    if self.controller.state == 'active':
                        # Loads operation mode parameters
                        energy_threshold = self.op_params.get('energy_threshold')
                        duty_cycle_factor = self.op_params.get('duty_cycle_factor') 

                        # Checks if stored energy in the battery and updates duty cycle of loads
                        if stored_energy < energy_threshold:
                            i = 0
                            # Updates each sensor's t idle
                            for sensor in self.sensors:
                                sensor.t_idle = duty_cycle_factor*self.sensors_ref_t_idle[i]
                                i += 1
                            # Updates controller's t idle
                            self.controller.t_idle = duty_cycle_factor*self.contr_ref_t_idle
                            # Updates communication's t sleep
                            self.communication.t_sleep = duty_cycle_factor*self.comm_ref_t_sleep         
                        else:
                            i = 0
                            # Updates each sensor's t idle
                            for sensor in self.sensors:
                                sensor.t_idle = self.sensors_ref_t_idle[i]
                                i += 1
                            # Updates controller's t idle
                            self.controller.t_idle = self.contr_ref_t_idle
                            # Updates communication's t sleep
                            self.communication.t_sleep = self.comm_ref_t_sleep 
                        if self.controller.timer < self.controller.t_active:
                            self.controller.timer += 1
                        else:
                            self.controller.timer = 1
                            self.controller.state = 'idle'

            # Updates each sensor's state
            for sensor in self.sensors:
                if sensor.t_idle == 0:
                    sensor.state = 'active'
                    sensor.sample_count += 1
                else:
                    if sensor.state == 'idle':
                        if sensor.timer < sensor.t_idle:
                            sensor.timer += 1
                        else:
                            sensor.timer = 1
                            sensor.state = 'active'
                    else:        
                        if sensor.state == 'active':
                            if sensor.timer < sensor.t_active:
                                sensor.timer += 1
                            else:
                                sensor.timer = 1
                                sensor.sample_count += 1
                                sensor.state = 'idle'

            # Updates communication's state
            if self.communication.t_sleep == 0 and self.communication.t_rx == 0:
                self.communication.state = 'transmitting'
                self.communication.tx_count += 1
            else:
                if self.communication.state == 'sleep':
                        if self.communication.timer < self.communication.t_sleep:
                            self.communication.timer += 1
                        else:
                            self.communication.timer = 1
                            self.communication.state = 'transmitting' 
                else:
                    if self.communication.state == 'transmitting':
                            if self.communication.timer < self.communication.t_tx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.tx_count += 1
                                if self.communication.t_rx == 0:
                                    self.communication.state = 'sleep'
                                else:
                                    self.communication.state = 'receiving'
                    else:
                        if self.communication.state == 'receiving':
                            if self.communication.timer < self.communication.t_rx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.rx_count += 1
                                self.communication.state = 'sleep'

        ##############################################################################
        #
        # Mode:         Stoplight With Two Modes And Battery Status Sense
        #
        # Description:  This operation mode alternates sampling interval between two
        #               options, the regular operation for battery above a given
        #               energy threshold and a low power operation with increased duty
        #               cycle factor.Before turning on sensor and communication devices,
        #               it checks if there is enough stored energy to perform load's 
        #               operation (sampling or communication)
        #
        ##############################################################################     
        if self.op_mode == 'stoplight2_battsense':

            import math

            # Updates controller's state
            if self.controller.t_idle == 0:
                self.controller.state = 'active'
                # Loads operation mode parameters
                energy_threshold = self.op_params.get('energy_threshold')
                duty_cycle_factor = self.op_params.get('duty_cycle_factor') 

                # Checks if stored energy in the battery and updates duty cycle of loads
                if stored_energy < energy_threshold:
                    i = 0
                    # Updates each sensor's t idle
                    for sensor in self.sensors:
                        sensor.t_idle = self.sensors_ref_t_idle[i] # duty_cycle_factor*
                        i += 1
                    # Updates controller's t idle
                    self.controller.t_idle = self.contr_ref_t_idle # duty_cycle_factor*
                    # Updates communication's t sleep
                    self.communication.t_sleep = self.comm_ref_t_sleep # duty_cycle_factor*        
                else:
                    i = 0
                    # Updates each sensor's t idle
                    for sensor in self.sensors:
                        sensor.t_idle = math.ceil(self.sensors_ref_t_idle[i]/duty_cycle_factor) # modified
                        i += 1
                    # Updates controller's t idle
                    self.controller.t_idle = math.ceil(self.contr_ref_t_idle/duty_cycle_factor) # modified
                    # Updates communication's t sleep
                    self.communication.t_sleep = math.ceil(self.comm_ref_t_sleep/duty_cycle_factor) # modified
            else:
                if self.controller.state == 'idle':
                    if self.controller.timer < self.controller.t_idle:
                        self.controller.timer += 1
                    else:
                        self.controller.timer = 1
                        self.controller.state = 'active'
                else:        
                    if self.controller.state == 'active':
                        # Loads operation mode parameters
                        energy_threshold = self.op_params.get('energy_threshold')
                        duty_cycle_factor = self.op_params.get('duty_cycle_factor') 

                        # Checks if stored energy in the battery and updates duty cycle of loads
                        if stored_energy < energy_threshold:
                            i = 0
                            # Updates each sensor's t idle
                            for sensor in self.sensors:
                                sensor.t_idle = self.sensors_ref_t_idle[i] #duty_cycle_factor*
                                i += 1
                            # Updates controller's t idle
                            self.controller.t_idle = self.contr_ref_t_idle #duty_cycle_factor*
                            # Updates communication's t sleep
                            self.communication.t_sleep = self.comm_ref_t_sleep #duty_cycle_factor*         
                        else:
                            i = 0
                            # Updates each sensor's t idle
                            for sensor in self.sensors:
                                sensor.t_idle = math.ceil(self.sensors_ref_t_idle[i]/duty_cycle_factor) # modified 
                                i += 1
                            # Updates controller's t idle
                            self.controller.t_idle = math.ceil(self.contr_ref_t_idle/duty_cycle_factor) # modified 
                            # Updates communication's t sleep
                            self.communication.t_sleep = math.ceil(self.comm_ref_t_sleep/duty_cycle_factor) # modified 
                        if self.controller.timer < self.controller.t_active:
                            self.controller.timer += 1
                        else:
                            self.controller.timer = 1
                            self.controller.state = 'idle'

            # Updates each sensor's state
            for sensor in self.sensors:
                if sensor.t_idle == 0:
                    sensor.state = 'active'
                    sensor.sample_count += 1
                else:
                    if sensor.state == 'idle':
                        if sensor.timer < sensor.t_idle:
                            sensor.timer += 1
                        else:
                            if stored_energy > (sensor.p_active*sensor.t_active)/60000.0:
                                sensor.timer = 1
                                sensor.state = 'active'
                    else:        
                        if sensor.state == 'active':
                            if sensor.timer < sensor.t_active:
                                sensor.timer += 1
                            else:
                                sensor.timer = 1
                                sensor.sample_count += 1
                                sensor.state = 'idle'

            # Updates communication's state
            if self.communication.t_sleep == 0 and self.communication.t_rx == 0:
                self.communication.state = 'transmitting'
                self.communication.tx_count += 1
            else:
                if self.communication.state == 'sleep':
                        if self.communication.timer < self.communication.t_sleep:
                            self.communication.timer += 1
                        else:
                            if stored_energy > (self.communication.p_tx*self.communication.t_tx)/60000.0:
                                self.communication.timer = 1
                                self.communication.state = 'transmitting' 
                else:
                    if self.communication.state == 'transmitting':
                            if self.communication.timer < self.communication.t_tx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.tx_count += 1
                                if self.communication.t_rx == 0:
                                    self.communication.state = 'sleep'
                                else:
                                    self.communication.state = 'receiving'
                    else:
                        if self.communication.state == 'receiving':
                            if self.communication.timer < self.communication.t_rx:
                                self.communication.timer += 1
                            else:
                                self.communication.timer = 1
                                self.communication.rx_count += 1
                                self.communication.state = 'sleep'
