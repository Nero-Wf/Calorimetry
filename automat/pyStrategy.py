class Strategy_Base:
    class operation_point_information:
        def __init__(self, temperature, flowrate_list):
            self.temperature = temperature
            self.flowrate_list = flowrate_list
        
        def get_temperature(self):
            return self.temperature

        def get_flowrate(self, idx):
            return self.flowrate_list[idx]
        
        def get_number_of_pumps(self):
            return len(self.flowrate_list)

    def get_operation_point(self):
        return None

    def push_value(self, value):
        return

    def point_complete(self):
        return False
        
    def has_error(self):
        return False

    def push_actual_flowrate(self, val):
        return 

    def get_finish_instruction(self):
        return None