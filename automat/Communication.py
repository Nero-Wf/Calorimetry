# This file contains the serial interface. For this purpose, the 
# library "serial" is used and adapted in the class "Handle" for 
# the own application.

# library/modules from python:
import serial

class Handle:
    PARITY_NONE = serial.PARITY_NONE
    PARITY_EVEN = serial.PARITY_EVEN
    PARITY_ODD = serial.PARITY_ODD
    
    def __init__(self, port, baudrate, parity, stopbits):
        self.com = serial.Serial(port, baudrate, 8, parity, stopbits)# , timeout=0) 

    def clear_input_buffer(self):
        self.com.reset_input_buffer()

    def send(self, msg):
        # print(msg.decode("ASCII"))
        self.com.write(msg)
    
    def receive(self):
        ans = self.com.read_until()
        # print(ans.decode("ASCII"))
        return ans