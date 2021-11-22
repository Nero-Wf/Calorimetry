# This file contains the state machine class for the automatization 
# and the following additional relevant classes and functions for 
# the construction of this class: the required state classes, which 
# can be assigned to the layers (A) and (B), functions for generating 
# the drivers of each device and a function concerning the user's input.

# library/modules from python:
import time
import math

# own scripts:
import automat.Calibration as Calibration
import automat.Calorimeter as Calorimeter
import automat.Communication as Communication
import automat.Dictionary as Dictionary
import automat.Fisher as Fisher
import automat.HPLC as HPLC
import automat.Lambda as Lambda
import automat.LayerB as LayerB
import automat.pyState as pyState

# layer (B) states:
class Set_Operating_Point(pyState.State_Base):
    def enter(self, operating_point_strategy, pump_list, thermostat, calorimeter, operation_point):
        super().enter("Set_Operating_Point")
        print("entering state Set_Operating_Point")
        self.operating_point_strategy = operating_point_strategy
        self.pump_list = pump_list
        self.thermostat = thermostat
        self.calorimeter = calorimeter
        self.operation_point = operation_point

    def __call__(self):
        current_temp = self.operation_point.get_temperature()
        self.calorimeter.set_target_Temp(current_temp)
        self.thermostat.set_target_temp(Dictionary.calorimeter_thermostat["calibration"].forward(current_temp))
        self.thermostat.activate_pump()

        pump_actual_flowrates = []       
        for idx in range(len(self.pump_list)):
            tmp_flowrate = self.operation_point.get_flowrate(idx)
            pump_actual_flowrates.append(self.pump_list[idx].set_target_flowrate(tmp_flowrate))
            if tmp_flowrate > 0.0:
                self.pump_list[idx].activate_pump()
            else:
                self.pump_list[idx].deactivate_pump()

        self.operating_point_strategy.push_actual_flowrate(pump_actual_flowrates)
        return "next"

class Operating(pyState.State_Base):
    def enter(self, operating_point_strategy, calodata, calodata_idx):
        super().enter("Operating")
        print("entering state Operating")
        self.operating_point_strategy = operating_point_strategy
        self.calodata = calodata
        self.calodata_idx = calodata_idx
        
    def __call__(self):
        push_empty = True
        while self.calodata_idx[0] < len(self.calodata):
            push_empty = False
            self.operating_point_strategy.push_value(self.calodata[self.calodata_idx[0]])
            self.calodata_idx[0] += 1
        if push_empty:
            self.operating_point_strategy.push_value(None)
            
        if self.operating_point_strategy.has_error():
            return "error"

        if self.operating_point_strategy.point_complete():
            return "next"

# layer (A) states:
class Apply_Configuration(pyState.State_Base):
    """This state runs the configuration state of all devices and puts them all in a deactivated mode."""
    def enter(self, pump_list, thermostat, calorimeter, calodata):
        super().enter("Apply_Configuration")
        print("entering state Apply_Config")
        self.pump_list = pump_list
        self.thermostat = thermostat
        self.calorimeter = calorimeter
        self.calodata = calodata

        self.deadline = time.monotonic_ns() + 60 * 1E9

    def __call__(self):

        for itm in self.pump_list:
            itm.tick()
        
        self.thermostat.tick()
        self.calorimeter.tick()

        if self.deadline < time.monotonic_ns():
            return "error"

        if self.thermostat.get_state() == "Error":
            return "error_thermostat"

        if self.calorimeter.get_state() == "Error":
            return "error_calorimeter"

        for itm in self.pump_list:
            if itm.get_state() == "Error":
                return "error_pump"

        for itm in self.pump_list:
            if not itm.get_state() == "Deactivated":
                return None

        if not self.thermostat.get_state() == "Deactivated":
            return None
        
        if len(self.calodata) == 0:
            return None

        return "next"

class List_Processing(pyState.State_Base):
    """This state ensures the processing of the operating points."""
    class factory:
        def __init__(self, pump_list, thermostat, calorimeter, calodata, operating_point_strategy):
            self.pump_list = pump_list
            self.thermostat = thermostat
            self.calorimeter = calorimeter
            self.operating_point_strategy = operating_point_strategy
            self.calodata = calodata
            self.calodata_idx = [len(calodata)]

        def create_state(self, state_name):
            if state_name == "Set_Operating_Point":
                tmp_operation_point = self.operating_point_strategy.get_operation_point()
                if tmp_operation_point is not None:
                    st = Set_Operating_Point()
                    st.enter(self.operating_point_strategy, self.pump_list, self.thermostat, self.calorimeter, tmp_operation_point)
                    return st
                else:
                    st = pyState.State_Base()
                    st.enter("Finished")
                    return st
            elif state_name == "Operating":
                st = Operating()
                st.enter(self.operating_point_strategy, self.calodata, self.calodata_idx)
                return st    
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, pump_list, thermostat, calorimeter, calodata, operating_point_strategy):
        super().enter("List_Processing")
        print("entering state List_Processing")
        self.tab = [
            ["Set_Operating_Point", "next",     "Operating"],
            ["Operating",           "next",     "Set_Operating_Point"],
            ["Operating",           "error",    "Error"],
            ]
        self.pump_list = pump_list
        self.thermostat = thermostat
        self.calorimeter = calorimeter
        self.fac = List_Processing.factory(pump_list, thermostat, calorimeter, calodata, operating_point_strategy)
        self.en = pyState.Engine(self.tab, self.fac, "Set_Operating_Point")
        self.en.enter()

    def __call__(self):
        for itm in self.pump_list:
            itm.tick()
        self.thermostat.tick()
        self.calorimeter.tick()

        self.en.tick()

        if self.thermostat.get_state() == "Error":
            return "error_thermostat"

        if self.calorimeter.get_state() == "Error":
            return "error_calorimeter"

        for itm in self.pump_list:
            if itm.get_state() == "Error":
                return "error_pump"

        if self.en.get_state() == "Error":
            return "error"

        if self.en.get_state() == "Finished":
            return "next"

    def exit(self):
        self.en.exit()
        super().exit()

class Deactivating(pyState.State_Base):
    """This state first switches off the pumps and then the thermostat. It is used for the regular shutdown as well as for the error shutdown."""
    def enter(self, state_name, leave_thermostat_on, pump_list, thermostat, calorimeter, operating_point_strategy, next_state):
        super().enter(state_name)
        print("entering state", state_name)
        
        if state_name.find("Error") != -1:
            if state_name == "Shutdown_Error_Pump":
                for itm in pump_list:
                    if itm.get_state() == "Error":
                        print(next_state, "from pump", itm.get_name())
            else:
                print(next_state)

        self.leave_thermostat_on = leave_thermostat_on
        self.pump_list = pump_list
        self.thermostat = thermostat
        self.calorimeter = calorimeter
        self.next_state = next_state
        
        self.counter = 0
        for itm in self.pump_list:
            itm.deactivate_pump()

        operating_point_strategy.get_finish_instruction()

    def __call__(self):
        
        for itm in self.pump_list:
            itm.tick()
        
        self.thermostat.tick()
        self.calorimeter.tick()

        if self.name == self.next_state:
            return None

        if self.counter == 0:
            for itm in self.pump_list:
                if not (itm.get_state() == "Deactivated" or itm.get_state() == "Error"):
                    return None
                
            if self.leave_thermostat_on:
                self.name = self.next_state
                return None
            else:
                self.counter = 1
                return None

        if self.counter == 1:
            self.thermostat.deactivate_pump()
            self.counter = 2
            return None

        if self.counter == 2:
            if not (self.thermostat.get_state() == "Deactivated" or self.thermostat.get_state() == "Error"):
                return None
            else:
                self.name = self.next_state
                return None

# generate the drivers:
# Achtung: Hier wechseln sich dummy und normales Communication_Handle 
# ab, je nachdem wie das Programm zuletzt verwendet wurde.
def generate_hplc(name, port, calibration_func, head, _PMin_ = None, _PMax_ = None):
    if head is None:
        raise Exception("No pump head is given")
    settings = HPLC.Driver.Settings(head)
    if not _PMin_ is None and not _PMax_ is None:
        settings.set_PMinMax(_PMin_, _PMax_)
    
    # ch = Communication.Handle(port, 9600, Communication.Handle.PARITY_NONE, 1)
    return HPLC.Driver(name, settings, calibration_func, HPLC.dummy_cmd_handle())

def generate_lambda(name, port, calibration_func, address):
    # ch = Communication.Handle(port, 2400, Communication.Handle.PARITY_ODD, 1)
    return Lambda.Driver(name, address, calibration_func, Lambda.dummy_cmd_handle())

def generate_fisher(port, _pump_speed = None, _ext_probe = None):
    settings = Fisher.Driver.Settings()
    if not _pump_speed is None:
        settings.set_pump_speed(_pump_speed)
    if not _ext_probe is None:
        settings.set_external_probe(_ext_probe)

    # ch = Communication.Handle(port, 9600, Communication.Handle.PARITY_NONE, 1)
    return Fisher.Driver("Fisher", settings, Fisher.dummy_cmd_handle())

def generate_calorimeter(port, datalist):
    ch = Communication.Handle(port, 9600, Communication.Handle.PARITY_NONE, 1)
    return Calorimeter.Driver("Calo", datalist, ch)

def initialize_thermostat(thermostat_specification):
    if len(thermostat_specification) == 0:
        raise Exception("There is no given specification for the thermostat")
    if len(thermostat_specification) == 1:
        return generate_fisher(thermostat_specification[0])
    
    _pump_speed = None
    _ext_probe = None

    num = len(thermostat_specification)-1
    for idx in range(num):
        if type(thermostat_specification[idx+1]) == str:
            _pump_speed = thermostat_specification[idx+1]
        elif type(thermostat_specification[idx+1]) == int or type(thermostat_specification[idx+1]) == float:
            _ext_probe = thermostat_specification[idx+1]
        else:
            raise Exception("Given thermostat setting cannot be handled")

    return generate_fisher(thermostat_specification[0], _pump_speed, _ext_probe)

def initialize_single_pumpdriver(pump_cfg_entry):
    length = len(pump_cfg_entry)
    if length < 2:
        raise Exception("Invalid list entry")
    
    pump_name = pump_cfg_entry[0]

    if pump_name == "HPLC A" or pump_name == "HPLC B" or pump_name == "HPLC C":
        if length == 2:           
            return generate_hplc(pump_name, pump_cfg_entry[1], Dictionary.pump_calibration[pump_name], Dictionary.pump_head[pump_name])
        if length == 4:
            return generate_hplc(pump_name, pump_cfg_entry[1], Dictionary.pump_calibration[pump_name], Dictionary.pump_head[pump_name], pump_cfg_entry[2], pump_cfg_entry[3])
        raise Exception("Invalid list entry")

    if pump_name == "Lambda 1" or pump_name == "Lambda 2" or pump_name == "Lambda 3":
        return generate_lambda(pump_name, pump_cfg_entry[1], Dictionary.pump_calibration[pump_name], Dictionary.lambda_address[pump_name])
    raise Exception("Invalid list entry")

def initialize_all_pumpdrivers(pump_list):

    ret = []
    for itm in pump_list:
        ret.append(initialize_single_pumpdriver(itm))
    return ret

# class and function concerning the user's input:
# Die Plausibilitaetspruefung ist noch in Bearbeitung.
def sanity_check_operation_point_list(liste, pump_list):
    number_of_pumps_in_system = len(pump_list)
    for itm in liste:
        if not number_of_pumps_in_system == itm.get_number_of_pumps():
            raise Exception("This operation point list does not fit with your pump cfg")

# state machine class for the automatization:
class matization:

    class factory:
        def __init__(self, operating_point_strategy, pump_list, thermostat, calorimeter, calodata):
            self.operating_point_strategy = operating_point_strategy
            self.pump_list = pump_list
            self.thermostat = thermostat
            self.calorimeter = calorimeter
            self.calodata = calodata

        def create_state(self, state_name):
            if state_name == "Apply_Configuration":
                st = Apply_Configuration()
                st.enter(self.pump_list, self.thermostat, self.calorimeter, self.calodata)
                return st
            elif state_name == "List_Processing":
                st = List_Processing()
                st.enter(self.pump_list, self.thermostat, self.calorimeter, self.calodata, self.operating_point_strategy)
                return st              
            elif state_name == "Finished":
                st = Deactivating()
                st.enter("Shutdown_{}".format(state_name), False, self.pump_list, self.thermostat, self.calorimeter, self.operating_point_strategy, state_name)
                return st
            elif state_name == "Error" or state_name == "Error_Calorimeter" or state_name == "Error_Thermostat" or state_name == "Error_Pump":
                st = Deactivating()
                st.enter("Shutdown_{}".format(state_name), False, self.pump_list, self.thermostat, self.calorimeter, self.operating_point_strategy, state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def __init__(self, operating_point_strategy, User_Pumps, User_Fisher, Portname_Calorimeter):
        self.tab = [
            ["Apply_Configuration",       "next",     "List_Processing"],
            ["List_Processing",           "next",     "Finished"],

            ["Apply_Configuration",        "error_calorimeter",     "Error_Calorimeter"],
            ["List_Processing",            "error_calorimeter",     "Error_Calorimeter"],

            ["Apply_Configuration",        "error_thermostat",      "Error_Thermostat"],
            ["List_Processing",            "error_thermostat",      "Error_Thermostat"],

            ["Apply_Configuration",        "error_pump",            "Error_Pump"],
            ["List_Processing",            "error_pump",            "Error_Pump"],
            
            ["Apply_Configuration",        "error",                 "Error"],
            ["List_Processing",            "error",                 "Error"],
            ]

        self.calodata = []
       
        self.thermostat  = initialize_thermostat(User_Fisher)
        self.calorimeter = generate_calorimeter(Portname_Calorimeter, self.calodata)
        self.pump_list = initialize_all_pumpdrivers(User_Pumps)

        #sanity_check_operation_point_list(operating_point_strategy, self.pump_list)

        self.fac = matization.factory(operating_point_strategy, self.pump_list, self.thermostat, self.calorimeter, self.calodata)
        self.en = pyState.Engine(self.tab, self.fac, "Apply_Configuration")
        self.en.enter()

    def tick(self):
        self.en.tick()

    def __del__(self):
        self.en.exit()

    def get_state(self):
        return self.en.get_state()
        