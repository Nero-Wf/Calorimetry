# This file contains the driver class for the HPLC pump and the 
# following additional relevant classes and functions for the 
# construction and simple testing of the driver class: the dummy 
# communication handle, two special substates, the response 
# checkers and all layer (A) states.

# library/modules from python:
import time
import re
import statistics 

# own scripts:
import automat.pyState as pyState
import automat.LayerC as LayerC
import automat.LayerB as LayerB

# dummy communication handle:
class dummy_cmd_handle():
    """This class can be used for testing the driver. Thus, no actual HPLC pump is needed."""
    def __init__(self):
        self.press = 0
        self.flow = 0
        self.pump = False
        self.resp = "0"

    def send(self, msg):
        # print(msg)
        if msg.decode("ASCII") == "PRESSURE?\r":
            if self.pump == False:
                self.resp = "PRESSURE:0\r"
            elif self.flow <= 0:
                self.resp = "PRESSURE:0\r"
            else:
                self.resp = "PRESSURE:30\r"
        elif msg.decode("ASCII") == "PMIN50: 0\r":
            self.resp = "PMIN50:OK\r"
        elif msg.decode("ASCII") == "PMIN50?\r":
            self.resp = "PMIN50:0\r"
        elif msg.decode("ASCII") == "PMAX50: 100\r":
            self.resp = "PMAX50:OK\r"
        elif msg.decode("ASCII") == "PMAX50?\r":
            self.resp = "PMAX50:100\r"  
        elif msg.decode("ASCII") == "FLOW: 06000\r":
            self.resp = "FLOW:OK\r"
            self.flow = 6000
        elif msg.decode("ASCII") == "FLOW: 00000\r":
            self.resp = "FLOW:OK\r"
            self.flow = 0
        elif msg.decode("ASCII") == "FLOW?\r":
            self.resp = "FLOW:{:05}\r".format(self.flow)
        elif msg.decode("ASCII") == "ON\r":
            self.pump = True
            self.resp = "ON:OK\r"
        elif msg.decode("ASCII") == "OFF\r":
            self.pump = False
            self.resp = "OFF:OK\r"
             
    def clear_input_buffer(self):
        # print("...clear...")
        return

    def receive(self):
        # print("...receive... {}".format(self.resp))
        return bytearray(self.resp.encode("ASCII"))

# two special substates: 
# These states are required by the HPLC pump to initially query the 
# system pressure, generate a reference value from it and later check 
# for this reference value.
class Save_Answer(pyState.State_Base):
    """This layer (C) state receives, checks and saves the response received."""
    def enter(self, name, timeout_ms, com_handle, datalist, boundaries, next_event, timeout_event, done_event):
        super().enter(name)
        self.com_handle = com_handle
        self.deadline = time.monotonic_ns() + timeout_ms * 1000000
        
        self.next_event = next_event
        self.timeout_event = timeout_event
        self.done_event = done_event
        
        self.datalist = datalist
        self.boundaries = boundaries
        self.response = bytearray()

    def __call__(self):
        end_of_frame = '\r'.encode("ASCII")
        tmp = self.com_handle.receive()
        for chr in tmp:
            if chr == end_of_frame[0]:    
                str_ans = find_pattern(self.response)
                self.datalist.append(float(str_ans))
                if len(self.datalist) < 10:
                    return self.next_event
                # calculation of the mean and standard deviation
                self.boundaries[0] = statistics.mean(self.datalist)
                self.boundaries[1] = statistics.stdev(self.datalist)
                return self.done_event
            self.response.append(chr)

        if time.monotonic_ns() > self.deadline:
            return self.timeout_event
        return None

class Send_And_Save_Data(pyState.State_Base):
    """This layer (B) state combines the substates sending a command and waiting and saving the response."""
    class factory:
        def __init__(self, datalist, boundaries, com_handle):
            self.datalist = datalist
            self.boundaries = boundaries
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Send":
                st = LayerC.Send_Command()
                st.enter(state_name, "PRESSURE?", self.com_handle, "next")
                return st
            elif state_name == "Save":
                st = Save_Answer()
                st.enter(state_name, 1000, self.com_handle, self.datalist, self.boundaries, "next", "timeout", "done")
                return st
            elif state_name == "Waiting":
                st = LayerB.Delay_State()
                st.enter(state_name, 500, "next")
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

    def enter(self, name, boundaries, com_handle):
        super().enter(name)
        self.tab = [
            ["Send",            "next",         "Save"],
            ["Save",            "next",         "Waiting"],
            ["Save",            "timeout",      "Error"],
            ["Save",            "done",         "Finished"],
            ["Waiting",         "next",         "Send"],
            ]
        self.datalist = []

        self.fac = Send_And_Save_Data.factory(self.datalist, boundaries, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Send")
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

# response checkers:
def find_pattern(ans):
    answer = ans.decode("ASCII")
    find_pattern = re.compile(r"\w*:(.*)")
    if not find_pattern.match(answer) is None:
        str_ans = find_pattern.match(answer).group(1)
        return str_ans
    else:
        return False

class check_response_base:
    """This class forms the basis for all other response checkers."""
    def __init__(self, resp):
        self.resp = resp

    def __call__(self, ans):
        # step 1: find pattern
        str_ans = find_pattern(ans)

        # step 2: compare pattern
        if str_ans == self.resp:
            return True
        return False

class check_ok(check_response_base):
    def __init__(self):
        super().__init__("OK")

class check_flow(check_response_base):
    def __init__(self, val):
        self.val = val

    def __call__(self, ans):
        str_ans = find_pattern(ans)
        if int(str_ans) == self.val:
            return True
        return False

# Die Ueberpruefung auf den Druck wird noch verbessert. Zur Zeit entsteht 
# der Fehler sobald man einmal außerhalb der Schranken liegt. Spaeter soll 
# erst eine gewisse Anzahl an hintereinander falsch liegender Druecke zum 
# Fehler fuehren.
class check_boundaries(check_response_base):
    def __init__(self, boundaries):
        self.lower = 0 # boundaries[0] - 5 * boundaries[1]
        self.upper = 220 # [0] + 20 * boundaries[1]

    def __call__(self, ans):
        str_ans = find_pattern(ans)
        val = float(str_ans) 
        if val <= self.upper and val >= self.lower:
            return True
        return False

class check_0(check_response_base):
    def __init__(self):
        super().__init__(0)

    def __call__(self, ans):
        str_ans = find_pattern(ans)
        val = float(str_ans)
        if val <= 40:
            return True
        return False 

# layer (A) states:
class Configuration(pyState.State_Base):
    """This state deactivates the HPLC pump and adjusts all initial settings."""
    class factory:
        def __init__(self, settings, com_handle):
            self.head = settings.get_head()
            self.settings = settings
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_Off":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "OFF", check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PRESSURE?", check_0(), self.com_handle, 0)
                return st
            elif state_name == "Set_PMin":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PMIN{:.2}: {:.0f}".format(str(self.head), self.settings.get_PMin()), check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_PMin":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PMIN{:.2}?".format(str(self.head)), check_response_base("{:.0f}".format(self.settings.get_PMin())) , self.com_handle, 0)
                return st
            elif state_name == "Set_PMax":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PMAX{:.2}: {:.0f}".format(str(self.head), self.settings.get_PMax()), check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_PMax":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PMAX{:.2}?".format(str(self.head)), check_response_base("{:.0f}".format(self.settings.get_PMax())), self.com_handle, 0)
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
            ["Check_Pump_State",    "next",     "Set_PMin"],
            ["Check_Pump_State",    "error",    "Error"],
            ["Set_PMin",            "next",     "Check_PMin"],
            ["Set_PMin",            "error",    "Error"],
            ["Check_PMin",          "next",     "Set_PMax"],
            ["Check_PMin",          "error",    "Error"],
            ["Set_PMax",            "next",     "Check_PMax"],
            ["Set_PMax",            "error",    "Error"],
            ["Check_PMax",          "next",     "Finished"],
            ["Check_PMax",          "error",    "Error"],
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

class Deactivated(pyState.State_Base):
    """This state checks whether the HPLC pump is still switched off and whether anything has changed in the settings and adjusts them if necessary."""
    class factory:
        def __init__(self, set_flowrate, com_handle):
            self.set_flow = set_flowrate
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PRESSURE?", check_0(), self.com_handle, 0)
                return st
            elif state_name == "Set_Flowrate":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "FLOW: {:05.0f}".format(self.set_flow[0]), check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_Flowrate":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "FLOW?", check_flow(self.set_flow[0]), self.com_handle, 0)
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

    def enter(self, name, target_flowrate, set_flowrate, com_handle):
        super().enter(name)
        self.target_flowrate = target_flowrate
        self.set_flowrate = set_flowrate
        self.pump_on_flag = False
        self.tab = [
            ["Check_Pump_State",  "next",         "Waiting"],
            ["Check_Pump_State",  "error",        "Error"],
            ["Waiting",           "next",         "Check_Pump_State"],
            ["Waiting",           "new_flowrate", "Set_Flowrate"],
            ["Set_Flowrate",      "next",         "Check_Flowrate"],
            ["Set_Flowrate",      "error",        "Error"],
            ["Check_Flowrate",    "next",         "Check_Pump_State"],
            ["Check_Flowrate",    "error",        "Error"],
            ]
        self.fac = Deactivated.factory(set_flowrate, com_handle)
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
    """This state checks whether the HPLC pump is still running at the correct flow rate and whether anything has changed in the settings and adjusts them if necessary."""
    class factory:
        def __init__(self, set_flowrate, com_handle):
            self.set_flow = set_flowrate
            self.com_handle = com_handle
            self.boundaries = [0,0]

        def create_state(self, state_name):
            if state_name == "Get_Boundaries":
                st = Send_And_Save_Data()
                st.enter(state_name, self.boundaries, self.com_handle)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PRESSURE?", check_boundaries(self.boundaries), self.com_handle, 0)
                return st
            elif state_name == "Set_Flowrate":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "FLOW: {:05.0f}".format(self.set_flow[0]), check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_Flowrate":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "FLOW?", check_flow(self.set_flow[0]), self.com_handle, 0)
                return st
            elif state_name == "Check_New_Flowrate":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "FLOW?", check_flow(self.set_flow[0]), self.com_handle, 0)
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

    def enter(self, name, target_flowrate, set_flowrate, com_handle):
        super().enter(name)
        self.target_flowrate = target_flowrate
        self.set_flowrate = set_flowrate
        self.pump_off_flag = False

        self.tab = [
            ["Get_Boundaries",      "next",         "Check_Pump_State"],
            ["Get_Boundaries",      "error",        "Error"],
            ["Check_Pump_State",    "next",         "Waiting"],
            ["Check_Pump_State",    "error",        "Error"],
            ["Waiting",             "next",         "Check_Flowrate"],
            ["Waiting",             "new_flowrate", "Set_Flowrate"],
            ["Set_Flowrate",        "next",         "Check_New_Flowrate"],
            ["Set_Flowrate",        "error",        "Error"],
            ["Check_New_Flowrate",  "next",         "Get_Boundaries"],
            ["Check_New_Flowrate",  "error",        "Error"],
            ["Check_Flowrate",      "next",         "Check_Pump_State"],
            ["Check_Flowrate",      "error",        "Error"],
            ]
        self.fac = Activated.factory(set_flowrate, com_handle)
        self.en = pyState.Engine(self.tab, self.fac, "Get_Boundaries")
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

class Deactivating(pyState.State_Base):
    """This state deactivates the HPLC pump and checks whether the shutdown has worked."""
    class factory:
        def __init__(self, com_handle):
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Pump_Off":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "OFF", check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Check_Pump_State":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "PRESSURE?", check_0(), self.com_handle, 0)
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
            ["Pump_Off",           "error",    "error"],
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

# driver class for the HPLC pump:
class Driver:
    
    class Settings:
        def __init__(self, head):
            self._PMin_ = 0
            self._PMax_ = 100
            self.head = head
            if self.head != 10 and self.head != 50:
                raise Exception("Invalid pump head")
        
        def get_PMin(self):
            return self._PMin_
        def get_PMax(self):
            return self._PMax_
        def get_head(self):
            return self.head

        def set_PMinMax(self, pmin, pmax):
            if pmin >= pmax:
                raise Exception("Minimum can't be above maximum")
            if pmin < 0:
                raise Exception("Minimum is out of boundaries")
            if self.head == 10 and pmax > 400:
                raise Exception("Maximum is out of boundaries")
            if self.head == 50 and pmax > 150:
                raise Exception("Maximum is out of boundaries")

            self._PMin_ = pmin
            self._PMax_ = pmax

    class factory:
        def __init__(self, settings, target_flowrate, set_flowrate, com_handle):
            self.settings = settings
            self.target_flowrate = target_flowrate
            self.set_flowrate = set_flowrate
            self.com_handle = com_handle

        def create_state(self, state_name):
            if state_name == "Configuration":
                st = Configuration()
                st.enter(state_name, self.settings, self.com_handle)
                return st
            elif state_name == "Deactivated":
                st = Deactivated()
                st.enter(state_name, self.target_flowrate, self.set_flowrate, self.com_handle)
                return st
            elif state_name == "Activated":
                st = Activated()
                st.enter(state_name, self.target_flowrate, self.set_flowrate, self.com_handle)
                return st
            elif state_name == "Deactivating":
                st = Deactivating()
                st.enter(state_name, self.com_handle)
                return st
            if state_name == "Activating":
                st = LayerB.Send_And_Check()
                st.enter(state_name, "ON", check_ok(), self.com_handle, 0)
                return st
            elif state_name == "Error":
                st = pyState.State_Base()
                st.enter(state_name)
                return st
            raise Exception("Unhandled State in Factory")

    def __init__(self, name, settings, calibration_func, com_handle):
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
        self.calibration_func = calibration_func
        self.target_flowrate = [0]
        self.set_flowrate = [float("nan")]

        self.target_pump_state = False

        self.fac = Driver.factory(settings, self.target_flowrate, self.set_flowrate, com_handle)
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

    # In the following, the functions are defined to obtain the settings for the HPLC pump (from outside).
    def set_target_flowrate(self, val):
        self.target_flowrate[0] = round(self.calibration_func.forward(val))
        return self.calibration_func.backward(self.target_flowrate[0])

    def activate_pump(self):
        self.target_pump_state = True

    def deactivate_pump(self):
        self.target_pump_state = False
