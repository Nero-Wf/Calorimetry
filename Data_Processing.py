#first we import all the modules needed for this script
from PySide6.QtCore import *
from PySide6.QtWidgets import QMainWindow

import threading


class Data_Processing(QMainWindow):
    def __init__(self):
        #this class will be the third tab, and we will do the calculations here
        super().__init__()


class Data_Thread(threading.Thread):
    #this is a class for a thread. It is used to continuously carry out a function while
    #letting us still use the rest of the GUI.
    def __init__(self, use, task):
        super(Data_Thread, self).__init__()
        self.use = use
        self.task = task
    def run(self):
        global stop_threads
        stop_threads = False
        while (stop_threads == False):
            self.task.datalogger(self.use)
            break
        print ("Thread ends")


def stop_all_Threads():
    """function to stop all threads via the stop command"""
    #we first declare this variable to be a global variable, and then set it to true.
    #this stops the loop of the thread.
    global stop_threads
    stop_threads = True
    print("all Threads stopped")
