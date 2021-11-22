# This file contains the driver class for the calorimeter and the 
# required state classes, which can be assigned to the layers (A) 
# and (B).

# library/modules from python:
import time
import re
import math
import os

# own scripts:
import automat.pyState as pyState

# layer (B) states:
class Read_Data(pyState.State_Base):
    """This state queries and stores the data from the calorimeter."""
    def enter(self, name, path, datalist, timeout_error_s, timeout_check_s, com_handle):
        super().enter(name)
        self.com_handle = com_handle
        self.pattern_values = re.compile(r"(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+).*[\r\n]")
        self.pattern_line_complete = re.compile(r"(.+)\n")   
    
        self.deadline_error_delta = timeout_error_s * 1E9
        self.deadline_error = time.monotonic_ns() + self.deadline_error_delta
        self.deadline_check = time.monotonic_ns() + timeout_check_s * 1E9

        self.datalist = datalist
        self.out_path = path
        self.current_line = ""

    def __call__(self):
        self.current_line = self.current_line + self.com_handle.receive().decode('utf-8')
        tmp = self.pattern_line_complete.match(self.current_line)

        while not tmp is None:
            self.deadline_error = time.monotonic_ns() + self.deadline_error_delta
            tmp_val = self.pattern_values.match(tmp.group(0))
            if not tmp_val is None:
                with open(self.out_path, 'a') as fout:
                    fout.write(tmp.group(1))
                    
                    line = []
                    for idx in range(11):
                        line.append(float(tmp_val.group(idx+1)))
                    self.datalist.append(line)
            
            self.current_line = self.current_line[tmp.end():]
            tmp = self.pattern_line_complete.match(self.current_line)

        if self.deadline_check < time.monotonic_ns():
            return "check"
        if self.deadline_error < time.monotonic_ns():
            return "error"
        return None

class Check_Set_Temp(pyState.State_Base):
    """This state checks the set temperature."""
    def enter(self, name, datalist, set_Temp):
        super().enter(name)
        self.list_Temp = float(datalist[len(datalist)-1][1])
        self.set_Temp = set_Temp

    def __call__(self):
        if math.isnan(self.set_Temp[0]):
            return "next"
        if float(self.set_Temp[0]) == self.list_Temp:
            return "next"
        return "error"

# layer (A) states:
class Clear(pyState.State_Base):
    """This state ensures a proper starting point for the calorimeter."""
    def enter(self, name, path, com_handle):
        super().enter(name)
        self.com_handle = com_handle
        self.out_path = path

    def __call__(self):
        if os.path.isfile(self.out_path):
            os.remove(self.out_path)

        self.com_handle.clear_input_buffer()

        return "next"

class Read_And_Check(pyState.State_Base):
    """This state combines the substates "Read_Data" and "Check_Set_Temp"."""
    class factory:
        def __init__(self, path, datalist, set_Temp, com_handle):
            self.datalist = datalist
            self.set_Temp = set_Temp
            self.com_handle = com_handle
            self.out_path = path

        def create_state(self, state_name):
            if state_name == "Read":
                st = Read_Data()
                st.enter(state_name, self.out_path, self.datalist, 7, 10, self.com_handle)
                return st
            elif state_name == "Check":
                st = Check_Set_Temp()
                st.enter(state_name, self.datalist, self.set_Temp)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, name, path, datalist, target_Temp, set_Temp, com_handle):
        super().enter(name)
        self.target_Temp = target_Temp
        self.set_Temp = set_Temp
        self.tab = [
            ["Read",    "check",        "Check"],
            ["Read",    "error",        "Error"],
            ["Check",   "next",         "Read"],
            ["Check",   "error",        "Error"],
            ]
        self.fac = Read_And_Check.factory(path, datalist, self.set_Temp, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Read")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Error":
            return "error"

        if not self.en.get_state() == "Read":
            return None
        
        if math.isfinite(self.target_Temp[0]) and not self.target_Temp[0] == self.set_Temp[0]:
            self.set_Temp[0] = self.target_Temp[0]
            return "new_set_Temp"
        
    def exit(self):
        self.en.exit()
        super().exit()

class Set_Temp(pyState.State_Base):
    """This state sets a new set temperature at the calorimeter."""
    def enter(self, name, set_Temp, com_handle):
        super().enter(name)
        self.com_handle = com_handle
        self.set_Temp = set_Temp

    def __call__(self):
        if math.isnan(self.set_Temp[0]):
            return "next"

        text = "<1,{:02.2f}>".format(float(self.set_Temp[0]))
        com = bytearray(text.encode('utf-8'))
        self.com_handle.send(com)
        return "next"

# driver class for the calorimeter:
class Driver:

    class factory:
        def __init__(self, datalist, target_Temp, set_Temp, com_handle):
            self.target_Temp = target_Temp
            self.set_Temp = set_Temp
            self.com_handle = com_handle

            self.datalist = datalist
            self.out_path = "test.log"

        def create_state(self, state_name):
            if state_name == "Clear":
                st = Clear()
                st.enter(state_name, self.out_path, self.com_handle)
                return st
            elif state_name == "Read_And_Check":
                st = Read_And_Check()
                st.enter(state_name, self.out_path, self.datalist, self.target_Temp, self.set_Temp, self.com_handle)
                return st
            elif state_name == "Set_Temp":
                st = Set_Temp()
                st.enter(state_name, self.set_Temp, self.com_handle)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def __init__(self, name, datalist, com_handle):
        self.name = name
        self.tab = [
            ["Clear",           "next",          "Read_And_Check"],
            ["Read_And_Check",  "new_set_Temp",  "Set_Temp"],
            ["Read_And_Check",  "error",         "Error"],
            ["Set_Temp",        "next",          "Read_And_Check"],
            ]
        self.target_Temp = [float("nan")]
        self.set_Temp = [float("nan")]

        self.fac = Driver.factory(datalist, self.target_Temp, self.set_Temp, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Clear")
        self.en.enter()

    def tick(self):
        self.en.tick()

    def __del__(self):
        self.en.exit()

    def get_state(self):
        return self.en.get_state()

    def get_name(self):
        return self.name

    # In the following, the functions are defined to obtain the settings for the calorimeter (from outside).
    def set_target_Temp(self, val):
        self.target_Temp[0] = val

