# This file contains the driver class for the Lambda pump and the 
# following additional relevant classes for the construction and 
# simple testing of the driver class: the dummy communication handle, 
# generation of the commands that will later be sent to the pump, 
# the response checker and all layer (A) states. 

# library/modules from python:
import time
import re

# own scripts:
import automat.pyState as pyState
import automat.LayerB as LayerB

# dummy communication handle:
class dummy_cmd_handle:
    """This class can be used for testing the driver. Thus, no actual Lambda pump is needed."""
    def __init__(self):
        self.resp = "<0201r1232D\r\n"

    def send(self, msg):
        # print(msg)
        if msg.decode("ASCII") == "#0201r000E8\r":
            self.resp = "<0102r0002D\r"
        elif msg.decode("ASCII") == "#0201r123EE\r":
            self.resp = "<0102r1232D\r"
        elif msg.decode("ASCII") == "#0201r321EE\r":
            self.resp = "<0102r3212D\r"

    def clear_input_buffer(self):
        # print("...clear...")
        return None
        
    def receive(self):
        # print("...receive... {}".format(self.resp))
        return bytearray(self.resp.encode("ASCII"))

# generation of the commands that will later be sent to the pump:
class build_set_msg:
    """This class builds the command with the checksum for setting a flow rate."""
    def __init__(self, address, ddd):
        self.address = address
        self.ddd = ddd

    def __call__(self):
        mm = 1
        step1 = "#{:02d}{:02d}r{:03.0f}".format(self.address, mm, self.ddd)
        qs = sum(bytearray(step1.encode("ASCII"))) & 0xFF
        msg = "{}{:02X}".format(step1, qs)
        
        return msg

class build_read_msg:
    """This class builds the command with the checksum for the query which flow rate is set."""
    def __init__(self, address):
        self.address = address

    def __call__(self):
        mm = 1
        step1 = "#{:02d}{:02d}G".format(self.address, mm)
        qs = sum(bytearray(step1.encode("ASCII"))) & 0xFF
        msg = "{}{:02X}".format(step1, qs)
        
        return msg

# response checker:
class check_response:
    """This class compares the received answer "ans" with the expected answer "resp"."""
    def __init__(self, resp):
        self.resp = resp

    def __call__(self, ans):
        # step 1: find pattern
        answer = ans.decode("ASCII")
        find_pattern = re.compile(r"<\d{4}(\w{1})(\d{3})\S*")
        if not find_pattern.match(answer) is None:
            lrinfo = find_pattern.match(answer).group(1)
            ddd = int(find_pattern.match(answer).group(2))
        else:
            return False

        # step 2: compare pattern
        if ddd == self.resp and lrinfo == "r":
            return True
        else:
            return False

# layer (A) states:
class Deactivating(pyState.State_Base):
    """This state deactivates the Lambda pump and checks whether the shutdown has worked."""
    class factory:
        def __init__(self, address, com_handle):
            self.address = address
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_Off":
                st = LayerB.Send()
                st.enter(state_name, build_set_msg(self.address, 0)(), self.com_handle, "next")
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, build_read_msg(self.address)(), check_response(0), self.com_handle, 0)
                return st
            elif state_name == "Finished":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, name, address, com_handle):
        super().enter(name)
        self.tab = [
            ["Pump_Off",           "next",     "Check_Pump_State"],
            ["Check_Pump_State",   "next",     "Finished"],
            ["Check_Pump_State",   "error",    "Error"],
            ]
        self.fac = Deactivating.factory(address, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Pump_Off")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Finished":
            return "next"
        if self.en.get_state() == "Error":
            return "error"
    
    def exit(self):
        self.en.exit()
        super().exit()     

class Deactivated(pyState.State_Base):
    """This state checks whether the Lambda pump is still switched off and waits whether the pump should be switched on again."""
    class factory:
        def __init__(self, address, com_handle):
            self.address = address
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, build_read_msg(self.address)(), check_response(0), self.com_handle, 0)
                return st
            elif state_name == "Waiting":
                st = LayerB.Delay_State()
                st.enter(state_name, 500, "next")
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, name, address, com_handle):
        super().enter(name)
        self.pump_on_flag = False
        self.tab = [
            ["Check_Pump_State",  "next",   "Waiting"],
            ["Check_Pump_State",  "error",  "Error"],
            ["Waiting",           "next",   "Check_Pump_State"],
            ]
        self.fac = Deactivated.factory(address, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Check_Pump_State")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Error":
            return "error"

        if not self.en.get_state() == "Waiting":
            return None
        
        if self.pump_on_flag:
            return "pump_on"

    def exit(self):
        self.en.exit()
        super().exit()
    
    def handle_event(self, event):
        if event == "request_pump_on":
            self.pump_on_flag = True
            return True
        return False

class Activating(pyState.State_Base):
    """This state activates the Lambda pump and checks whether the switch-on has worked."""
    class factory:
        def __init__(self, set_flowrate, address, com_handle):
            self.flow = set_flowrate
            self.address = address
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_On":
                st = LayerB.Send()
                st.enter(state_name, build_set_msg(self.address, self.flow[0])(), self.com_handle, "next")
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, build_read_msg(self.address)(), check_response(self.flow[0]), self.com_handle, 0)
                return st
            elif state_name == "Finished":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, name, target_flowrate, set_flowrate, address, com_handle):
        super().enter(name)
        self.tab = [
            ["Pump_On",            "next",     "Check_Pump_State"],
            ["Check_Pump_State",   "next",     "Finished"],
            ["Check_Pump_State",   "error",    "Error"],
            ]
        set_flowrate[0] = target_flowrate[0]
        self.fac = Activating.factory(set_flowrate, address, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Pump_On")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Finished":
            return "next"
        if self.en.get_state() == "Error":
            return "error"

    def exit(self):
        self.en.exit()
        super().exit()

class Activated(pyState.State_Base):
    """This state checks whether the Lambda pump is still running at the correct flow rate and whether anything has changed in the settings and adjusts them if necessary."""
    class factory:
        def __init__(self, set_flowrate, address, com_handle):
            self.flow = set_flowrate
            self.address = address
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, build_read_msg(self.address)(), check_response(self.flow[0]), self.com_handle, 0)
                return st
            elif state_name == "Waiting":
                st = LayerB.Delay_State()
                st.enter(state_name, 500, "next")
                return st
            elif state_name == "Set_Flowrate":
                st = LayerB.Send()
                st.enter(state_name, build_set_msg(self.address, self.flow[0])(), self.com_handle, "next")
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def enter(self, name, target_flowrate, set_flowrate, address, com_handle):
        super().enter(name)
        self.target_flowrate = target_flowrate
        self.set_flowrate = set_flowrate
        self.pump_off_flag = False

        self.tab = [
            ["Check_Pump_State",    "next",         "Waiting"],
            ["Check_Pump_State",    "error",        "Error"],
            ["Waiting",             "next",         "Check_Pump_State"],
            ["Waiting",             "new_flowrate", "Set_Flowrate"],
            ["Set_Flowrate",        "next",         "Check_Pump_State"],
            ]
        self.fac = Activated.factory(set_flowrate, address, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Check_Pump_State")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Error":
            return "error"

        if not self.en.get_state() == "Waiting":
            return None
        
        if not self.target_flowrate[0] == self.set_flowrate[0]:
            self.set_flowrate[0] = self.target_flowrate[0]
            self.en.handle_event("new_flowrate")
            return None
        elif self.pump_off_flag:
            return "pump_off"
    
    def exit(self):
        self.en.exit()
        super().exit()

    def handle_event(self, event):
        if event == "request_pump_off":
            self.pump_off_flag = True
            return True
        return False

# driver class for the Lambda pump:
class Driver:
    
    class factory:
        def __init__(self, address, target_flowrate, set_flowrate, com_handle):
            self.address = address
            self.target_flowrate = target_flowrate
            self.set_flowrate = set_flowrate
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Deactivating":
                st = Deactivating()
                st.enter(state_name, self.address, self.com_handle)
                return st
            elif state_name == "Deactivated":
                st = Deactivated()
                st.enter(state_name, self.address, self.com_handle)
                return st
            elif state_name == "Activated":
                st = Activated()
                st.enter(state_name, self.target_flowrate, self.set_flowrate, self.address, self.com_handle)
                return st
            elif state_name == "Activating":
                st = Activating()
                st.enter(state_name, self.target_flowrate, self.set_flowrate, self.address, self.com_handle)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def __init__(self, name, address, calibration_func, com_handle):
        self.name = name
        self.tab = [
            ["Deactivating",            "next",     "Deactivated"],
            ["Deactivating",            "error",    "Error"],
            ["Deactivated",             "pump_on",  "Activating"],
            ["Deactivated",             "error",    "Error"],
            ["Activating",              "next",     "Activated"],
            ["Activating",              "error",    "Error"],
            ["Activated",               "pump_off", "Deactivating"],
            ["Activated",               "error",    "Error"],
            ]
        self.calibration_func = calibration_func
        self.target_flowrate = [0]
        self.set_flowrate = [-1]

        self.target_pump_state = False

        self.fac = Driver.factory(address, self.target_flowrate, self.set_flowrate, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Deactivating")
        self.en.enter()

    def tick(self):
        self.en.tick()
        
        if self.en.get_state() == "Deactivated" and self.target_pump_state and self.target_flowrate[0] != 0:
            self.en.handle_event("request_pump_on")
            return

        if self.en.get_state() == "Activated" and (not self.target_pump_state or self.target_flowrate[0] == 0):
            self.en.handle_event("request_pump_off")
            return

    def __del__(self):
        self.en.exit()

    def get_state(self):
        return self.en.get_state()
    
    def get_name(self):
        return self.name

    # In the following, the functions are defined to obtain the settings for the Lambda pump (from outside).
    def set_target_flowrate(self, val):
        self.target_flowrate[0] = round(self.calibration_func.forward(val))
        return self.calibration_func.backward(self.target_flowrate[0])

    def activate_pump(self):
        self.target_pump_state = True

    def deactivate_pump(self):
        self.target_pump_state = False

