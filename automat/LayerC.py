# This file contains relevant classes for the generation of the HPLC, 
# Lambda and Thermostat drivers. The classes listed in this file are 
# possible states on the lowest (third) layer (C). Higher layers (A) 
# and (B) can be built from these classes.

# library/modules from python:
import time 

# own scripts:
import automat.pyState as pyState

class Send_Command(pyState.State_Base):
    """This state sends a command to a device."""
    def enter(self, name, msg, com_handle, next_event):
        super().enter(name)
        self.msg = bytearray((msg + "\r").encode("ASCII"))
        self.com_handle = com_handle
        self.next_event = next_event

    def __call__(self):
        self.com_handle.clear_input_buffer()
        self.com_handle.send(self.msg)
        return self.next_event

class Wait_For_Answer(pyState.State_Base):
    """This state waits for the response of a device and checks whether it corresponds to the expected response."""
    def enter(self, name, timeout_ms, com_handle, response_checker, next_event, timeout_event, retry_count, retry_event, error_event):
        super().enter(name)
        self.com_handle = com_handle
        self.deadline = time.monotonic_ns() + timeout_ms * 1000000
        
        self.response_checker = response_checker
        
        self.next_event = next_event
        self.timeout_event = timeout_event
        self.retry_count = retry_count
        self.retry_event = retry_event
        self.error_event = error_event
        
        self.response = bytearray()

    def __call__(self):
        end_of_frame = '\r'.encode("ASCII")
        tmp = self.com_handle.receive()
        for chr in tmp:
            if chr == end_of_frame[0]:
                if self.response_checker(self.response):
                    return self.next_event
                if self.retry_count[0] > 0:
                    self.retry_count[0] -= 1
                    return self.retry_event
                print(self.response)
                return self.error_event
            self.response.append(chr)

        if time.monotonic_ns() > self.deadline:
            return self.timeout_event
        return None

        