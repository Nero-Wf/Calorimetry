# This file contains relevant classes for the generation of the HPLC, 
# Lambda and Thermostat drivers. The classes listed in this file are 
# possible states on the middle (second) layer (B). Higher layers (A) 
# can be built from these classes.

# library/modules from python:
import time

# own scripts:
import automat.pyState as pyState
import automat.LayerC as LayerC

class Send_And_Check(pyState.State_Base):
    """This state combines the substates sending a command, waiting for the response and checking the response."""
    class factory:
        def __init__(self, msg, checker, com_handle, retry_count):
            self.msg = msg
            self.checker = checker
            self.com_handle = com_handle
            self.retry_count = [retry_count]

        def create_state(self, state_name):
            if state_name == "Send":
                st = LayerC.Send_Command()
                st.enter(state_name, self.msg, self.com_handle, "next")
                return st
            elif state_name == "Check":
                st = LayerC.Wait_For_Answer()
                st.enter(state_name, 1000, self.com_handle, self.checker, "next", "timeout", self.retry_count, "retry", "error")
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

    def enter(self, name, msg, checker, com_handle, retry_count):
        super().enter(name)
        self.tab = [
            ["Send",  "next",    "Check"],
            ["Check", "next",    "Finished"],
            ["Check", "retry",   "Send"],
            ["Check", "timeout", "Error"],
            ["Check", "error",   "Error"],
            ]
        self.fac = Send_And_Check.factory(msg, checker, com_handle, retry_count)
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

class Delay_State(pyState.State_Base):
    """This state waits for the given time."""
    def enter(self, name, delay_time_ms, next_event):
        super().enter(name)
        self.deadline = time.monotonic_ns() + delay_time_ms * 1000000
        self.next_event = next_event
    
    def __call__(self):
        if time.monotonic_ns() > self.deadline:
            return self.next_event
        return None

# Special case for the Lambda pump: In case no response is expected to 
# a sent command, Send_And_Check cannot be used on layer (B), instead 
# Send_Command from layer (C) is used.
from automat.LayerC import Send_Command as Send
