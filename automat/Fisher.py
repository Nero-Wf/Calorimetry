# This file contains the driver class for the Fisher thermostat and 
# the following additional relevant classes for the construction and 
# simple testing of the driver class: the dummy communication handle, 
# the response checkers and all layer (A) states.

# library/modules from python:
import time
import re
import math

# own scripts:
import automat.pyState as pyState
import automat.LayerB as LayerB

# dummy communication handle:
class dummy_cmd_handle():
    """This class can be used for testing the driver. Thus, no actual Fisher thermostat is needed."""
    def __init__(self):
        self.resp = "OK\r\n"
        self.val = 0
        self.resp_RO = "0"
        self.resp_RPS = "M"
        self.resp_RE = "0"

    def send(self, msg):
        # print(msg)
        if msg.decode("ASCII") == "RO\r":
            self.resp = "{}\r".format(self.resp_RO)
        elif msg.decode("ASCII") == "SO 1\r":
            self.resp = "OK\r\n"
            self.resp_RO = "1"
        elif msg.decode("ASCII") == "SO 0\r":
            self.resp = "OK\r\n"
            self.resp_RO = "0"
        elif msg.decode("ASCII") == "STU C\r":
            self.resp = "OK\r\n"
        elif msg.decode("ASCII") == "RTU\r":
            self.resp = "C\r\n"
        elif msg.decode("ASCII") == "SPS M\r":
            self.resp = "OK\r\n"
            self.resp_RPS = "M"
        elif msg.decode("ASCII") == "SPS L\r":
            self.resp = "OK\r\n"
            self.resp_RPS = "L"
        elif msg.decode("ASCII") == "SPS H\r":
            self.resp = "OK\r\n"
            self.resp_RPS = "H"
        elif msg.decode("ASCII") == "RPS\r":
            self.resp = "{}\r".format(self.resp_RPS)
        elif msg.decode("ASCII") == "SE 0\r":
            self.resp = "OK\r\n"
            self.resp_RE = "0"
        elif msg.decode("ASCII") == "SE 1\r":
            self.resp = "OK\r\n"
            self.resp_RE = "1"
        elif msg.decode("ASCII") == "RE\r":
            self.resp = "{}\r".format(self.resp_RE)
        elif msg.decode("ASCII") == "RS\r":
            self.resp = "{:.1f}C\r".format(self.val)
        elif msg.decode("ASCII") == "SS 26.0\r":
            self.resp = "OK\r\n"
            self.val = 26.0
        elif msg.decode("ASCII") == "SS 25.0\r":
            self.resp = "OK\r\n"
            self.val = 25.0

    def clear_input_buffer(self):
        # print("...clear...")
        return
    def receive(self):
        # print("...receive... {}".format(self.resp))
        return bytearray(self.resp.encode("ASCII"))

# response checkers:
class check_response_base:
    """This class forms the basis for all other response checkers."""
    def __init__(self, resp):
        self.resp = resp

    def __call__(self, ans):
        if ans.decode("ASCII") == self.resp:
            return True
        return False

class check_OK(check_response_base):
    def __init__(self):
        super().__init__("OK")

class check_0(check_response_base):
    def __init__(self):
        super().__init__("0")

class check_1(check_response_base):
    def __init__(self):
        super().__init__("1")

class check_set_Temp(check_response_base):
    def __init__(self, resp):
        self.resp = float(resp)
    
    def __call__(self, ans):
        answer = ans.decode("ASCII")
        find_pattern = re.compile(r"([\d\.]*)C")
        if not find_pattern.match(answer) is None:
            value = float(find_pattern.match(answer).group(1))
        else:
            return False

        if value == self.resp:
            return True
        return False

# layer (A) states:
class Deactivated(pyState.State_Base):
    """This state checks whether the pump of the thermostat is still switched off and whether the set temperature is correct. A different set temperature can be set and the pump can be activated from outside."""
    class factory:
        def __init__(self, set_temp, com_handle):
            self.set_temp = set_temp
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RO", check_0(), self.com_handle, 3)
                return st
            elif state_name == "Set_Temp":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SS {:.1f}".format(self.set_temp[0]), check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Temp":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RS", check_set_Temp(self.set_temp[0]), self.com_handle, 3)
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

    def enter(self, name, target_temp, set_temp, com_handle):
        super().enter(name)
        self.target_temp = target_temp
        self.set_temp = set_temp
        self.pump_on_flag = False

        self.tab = [
            ["Check_Pump_State",    "next",         "Waiting"],
            ["Check_Pump_State",    "error",        "Error"],
            ["Waiting",             "next",         "Check_Pump_State"],
            ["Waiting",             "new_temp",     "Set_Temp"],
            ["Set_Temp",            "next",         "Check_Temp"],
            ["Set_Temp",            "error",        "Error"],
            ["Check_Temp",          "next",         "Check_Pump_State"],
            ["Check_Temp",          "error",        "Error"],
            ]
        self.fac = Deactivated.factory(set_temp, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Check_Pump_State")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Error":
            return "error"

        if not self.en.get_state() == "Waiting":
            return None
        
        if math.isfinite(self.target_temp[0]) and not self.target_temp[0] == self.set_temp[0]:
            self.set_temp[0] = self.target_temp[0]
            self.en.handle_event("new_temp")
            return None
        elif self.pump_on_flag:
            return "pump_on"

    def exit(self):
        self.en.exit()
        super().exit()
    
    def handle_event(self, event):
        if event == "request_pump_on":
            self.pump_on_flag = True
            return True
        return False

class Activated(pyState.State_Base):
    """This state checks whether the pump of the thermostat is still switched on and whether the set temperature is correct. A different set temperature can be set and the pump can be deactivated from outside."""
    class factory:
        def __init__(self, set_temp, com_handle):
            self.set_temp = set_temp
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RO", check_1(), self.com_handle, 3)
                return st
            elif state_name == "Set_Temp":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SS {:.1f}".format(self.set_temp[0]), check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Temp":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RS", check_set_Temp(self.set_temp[0]), self.com_handle, 3)
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

    def enter(self, name, target_temp, set_temp, com_handle):
        super().enter(name)
        self.target_temp = target_temp
        self.set_temp = set_temp
        self.pump_off_flag = False

        self.tab = [
            ["Check_Pump_State",    "next",     "Waiting"],
            ["Check_Pump_State",    "error",    "Error"],
            ["Waiting",             "next",     "Check_Temp"],
            ["Waiting",             "new_temp", "Set_Temp"],
            ["Set_Temp",            "next",     "Check_Temp"],
            ["Set_Temp",            "error",    "Error"],
            ["Check_Temp",          "next",     "Check_Pump_State"],
            ["Check_Temp",          "error",    "Error"],
            ]
        self.fac = Activated.factory(set_temp, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Check_Pump_State")
        self.en.enter()

    def __call__(self):
        self.en.tick()

        if self.en.get_state() == "Error":
            return "error"

        if not self.en.get_state() == "Waiting":
            return None
        
        if math.isfinite(self.target_temp[0]) and not self.target_temp[0] == self.set_temp[0]:
            self.set_temp[0] = self.target_temp[0]
            self.en.handle_event("new_temp")
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

class Activating(pyState.State_Base):
    """This state activates the pump of the thermostat and checks whether the switch-on has worked."""
    class factory:
        def __init__(self, com_handle):
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_On":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SO 1", check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RO", check_1(), self.com_handle, 3)
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

    def enter(self, name, com_handle):
        super().enter(name)
        self.tab = [
            ["Pump_On",            "next",     "Check_Pump_State"],
            ["Pump_On",            "error",    "Error"],
            ["Check_Pump_State",   "next",     "Finished"],
            ["Check_Pump_State",   "error",    "Error"],
            ]
        self.fac = Activating.factory(com_handle)
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

class Deactivating(pyState.State_Base):
    """This state deactivates the pump of the thermostat and checks whether the shutdown has worked."""
    class factory:
        def __init__(self, com_handle):
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_Off":
                st = LayerB.Send_And_Check()
                st.enter( state_name, "SO 0", check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter( state_name, "RO", check_0(), self.com_handle, 3)
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

    def enter(self, name, com_handle):
        super().enter(name)
        self.tab = [
            ["Pump_Off",           "next",     "Check_Pump_State"],
            ["Pump_Off",           "error",    "Error"],
            ["Check_Pump_State",   "next",     "Finished"],
            ["Check_Pump_State",   "error",    "Error"],
            ]
        self.fac = Deactivating.factory(com_handle)
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

class Configuration(pyState.State_Base):
    """This state deactivates the pump of the thermostat and adjusts all initial settings."""
    class factory:
        def __init__(self, settings, com_handle):
            self.settings = settings
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_Off":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SO 0", check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RO", check_0(), self.com_handle, 3)
                return st
            elif state_name == "Set_Temp_Unit":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "STU C", check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Temp_Unit":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RTU", check_response_base("C") , self.com_handle, 3)
                return st
            elif state_name == "Set_Pump_Speed":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SPS {}".format(self.settings.get_pump_speed()),  check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_Pump_Speed":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RPS", check_response_base(self.settings.get_pump_speed()), self.com_handle, 3)
                return st
            elif state_name == "Set_External_Probe":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "SE {}".format(self.settings.get_external_probe()), check_OK(), self.com_handle, 3)
                return st
            elif state_name == "Check_External_Probe":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "RE", check_response_base("{}".format(self.settings.get_external_probe())), self.com_handle, 3)
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

    def enter(self, name, settings, com_handle):
        super().enter(name)
        self.tab = [
            ["Pump_Off",            "next",     "Check_Pump_State"],
            ["Pump_Off",            "error",    "Error"],
            ["Check_Pump_State",    "next",     "Set_Temp_Unit"],
            ["Check_Pump_State",    "error",    "Error"],
            ["Set_Temp_Unit",       "next",     "Check_Temp_Unit"],
            ["Set_Temp_Unit",       "error",    "Error"],
            ["Check_Temp_Unit",     "next",     "Set_Pump_Speed"],
            ["Check_Temp_Unit",     "error",    "Error"],
            ["Set_Pump_Speed",      "next",     "Check_Pump_Speed"],
            ["Set_Pump_Speed",      "error",    "Error"],
            ["Check_Pump_Speed",    "next",     "Set_External_Probe"],
            ["Check_Pump_Speed",    "error",    "Error"],
            ["Set_External_Probe",  "next",     "Check_External_Probe"],
            ["Set_External_Probe",  "error",    "Error"],
            ["Check_External_Probe","next",     "Finished"],
            ["Check_External_Probe","error",    "Error"],
            ]
        self.fac = Configuration.factory(settings, com_handle)
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

# driver class for the Fisher thermostat: 
class Driver:
    
    class Settings:
        def __init__(self):
            self._pump_speed = "L"
            self._ext_probe = 0
        
        def get_pump_speed(self):
            return self._pump_speed
        def get_external_probe(self):
            return self._ext_probe
        def set_pump_speed(self, val):
            if val == 'L' or val == 'M' or val == 'H':
                self._pump_speed = val
                return
            raise Exception("Invalid value (L, M, H)")
        def set_external_probe(self, val):
            if val == 0 or val == 1:
                self._ext_probe = val
                return
            raise Exception("Invalid value (0, 1)")

    class factory:
        def __init__(self, settings, target_temp, set_temp, com_handle):
            self.settings = settings
            self.target_temp = target_temp
            self.set_temp = set_temp
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Configuration":
                st = Configuration()
                st.enter(state_name, self.settings, self.com_handle)
                return st
            elif state_name == "Deactivated":
                st = Deactivated()
                st.enter(state_name, self.target_temp, self.set_temp, self.com_handle)
                return st
            elif state_name == "Activated":
                st = Activated()
                st.enter(state_name, self.target_temp, self.set_temp, self.com_handle)
                return st
            elif state_name == "Deactivating":
                st = Deactivating()
                st.enter(state_name, self.com_handle)
                return st
            elif state_name == "Activating":
                st = Activating()
                st.enter(state_name, self.com_handle)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def __init__(self, name, settings, com_handle):
        self.name = name
        self.tab = [
            ["Configuration",           "next",         "Deactivated"],
            ["Configuration",           "error",        "Error"],
            ["Deactivated",             "pump_on",      "Activating"],
            ["Deactivated",             "error",        "Error"],
            ["Activating",              "next",         "Activated"],
            ["Activating",              "error",        "Error"],
            ["Activated",               "pump_off",     "Deactivating"],
            ["Activated",               "error",        "Error"],
            ["Deactivating",            "next",         "Deactivated"],
            ["Deactivating",            "error",        "Error"],
            ]
        self.target_temp = [float("nan")]
        self.set_temp = [float("nan")]

        self.target_pump_state = False

        self.fac = Driver.factory(settings, self.target_temp, self.set_temp, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Configuration")
        self.en.enter()

    def tick(self):
        self.en.tick()

        if self.en.get_state() == "Configuration":
            return
        
        if self.en.get_state() == "Deactivated" and self.target_pump_state:
            self.en.handle_event("request_pump_on")
            return

        if self.en.get_state() == "Activated" and not self.target_pump_state:
            self.en.handle_event("request_pump_off")
            return

    def __del__(self):
        self.en.exit()

    def get_state(self):
        return self.en.get_state()

    def get_name(self):
        return self.name 

    # In the following, the functions are defined to obtain the settings for the Fisher thermostat (from outside).
    def set_target_temp(self, val):
        self.target_temp[0] = val
    
    def activate_pump(self):
        self.target_pump_state = True

    def deactivate_pump(self):
        self.target_pump_state = False

