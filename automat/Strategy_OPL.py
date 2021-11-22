# library/modules from python:
import time
import math
from enum import Enum

# own scripts:
import pyStrategy

class operation_point_list_entry:
    """This class turns the user's input into an object, making it easier to handle the operating points."""
    def __init__(self, time_ms, temperature, flowrate_list):
        self.time_ms = time_ms
        self.temperature = temperature
        self.flowrate_list = flowrate_list
    
    def get_time_ms(self):
        return self.time_ms

    def get_temperature(self):
        return self.temperature

    def get_flowrate(self, idx):
        return self.flowrate_list[idx]
    
    def get_number_of_pumps(self):
        return len(self.flowrate_list)

class Operation_Point_List (pyStrategy.Strategy_Base):
    class States(Enum):
        TEMPERATURE_EQUILIBRATION = 0,
        SETTING_DEADLINE = 1,
        WAITING_FOR_DEADLINE = 2,

    def __init__(self, operation_point_list):
        self.list = operation_point_list
        self.idx = 0
        self.cur_temp = float("NaN")
        self.cur_deadline = 0
        self.cur_operation_point = None
        self.state = Operation_Point_List.States.TEMPERATURE_EQUILIBRATION
        self.datalist = []
        
    def get_operation_point(self):
        if not self.idx < len(self.list):
            self.cur_operation_point = None
            return None

        self.cur_operation_point = self.list[self.idx]
        if not self.cur_operation_point.get_temperature() == self.cur_temp:
            self.cur_deadline = time.monotonic_ns() + 10 * 60 * 1E9
            self.state = Operation_Point_List.States.TEMPERATURE_EQUILIBRATION
            self.cur_temp =  self.cur_operation_point.get_temperature()
            return pyStrategy.Strategy_Base.operation_point_information(self.cur_temp, [0] * self.cur_operation_point.get_number_of_pumps())
        
        self.state = Operation_Point_List.States.SETTING_DEADLINE
        self.idx += 1
        return pyStrategy.Strategy_Base.operation_point_information(self.cur_temp, self.cur_operation_point.flowrate_list)

    def push_value(self, line):
        if line is not None:
            self.datalist.append(line)

    def point_complete(self):
        if self.state == Operation_Point_List.States.TEMPERATURE_EQUILIBRATION:
            val = 10
            if len(self.datalist) < val:
                return False
        
            for col_idx in [2, 3, 4]:
                valid_count = 0
                for idx in range(val):
                    if abs(self.datalist[len(self.datalist)-1-idx][col_idx] - self.cur_operation_point.get_temperature()) < 0.1:
                        valid_count += 1
                if valid_count < math.ceil(val*0.9):
                    # return False
                    return True
            return True
        elif self.state == Operation_Point_List.States.SETTING_DEADLINE:
            self.cur_deadline = time.monotonic_ns() + self.cur_operation_point.get_time_ms() * 1E6
            self.state = Operation_Point_List.States.WAITING_FOR_DEADLINE
            return False
        elif self.state == Operation_Point_List.States.WAITING_FOR_DEADLINE:
            if self.cur_deadline < time.monotonic_ns():
                return True
            else:
                return False
        raise Exception("You should not land here")

    def has_error(self):
        if not self.state == Operation_Point_List.States.TEMPERATURE_EQUILIBRATION:
            return False

        if self.cur_deadline < time.monotonic_ns():
            print("set_temp is not reached at the reactor")
            return True
        return False




# liste = [
#     operation_point_list_entry(3, 25, [123]),
#     operation_point_list_entry(3, 25, [234]),
#     operation_point_list_entry(3, 30, [345]),
# ]

# op_str = Operation_Point_List(liste)

# op = op_str.get_operation_point()
# if op is not None:
#     print(op.get_flowrate(0))
# while op is not None:
#     op_str.push_value([0, 0, op.get_temperature(), op.get_temperature(), op.get_temperature()])
#     if op_str.has_error():
#         raise Exception("timeout Error")
#     if op_str.point_complete():
#         op = op_str.get_operation_point()
#         if op is not None:
#             print(op.get_flowrate(0))
