#first we import all the modules needed for this script
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib.animation as animation

import glob
import os
import openpyxl
from openpyxl import load_workbook

import threading
import serial
import time

import automat.Calorimeter as Calorimeter
import automat.Auto as Auto
import automat.Strategy_OCAE as Strategy_OCAE


#This is our top level window that we see when we start the script
#In it, we have three tabs or pages, which are made up of three windows
class TopLevelWindow(QWidget):

    def __init__(self):
        #first we start with this function, to call the initialization of the parent class "QWidget" before we start with our own __init__
        super().__init__()

        #we start with setting the title of the main window and the geometry of it
        self.setWindowTitle("AutoOpt")
        self.setGeometry(50,50,1450,700)

        #now we create the tabs in which our three sub-windows will go in
        oTabWidget = QTabWidget(self)

        #now we create the three sub-windows from the three classes below
        oPage1 = Initialization()
        oPage2 = Graph(oPage1)
        oPage3 = Data_Processing()

        #here we set some margins so that the windows don't touch the main window
        for i in (oPage1, oPage2, oPage3):
            i.setContentsMargins(20,20,20,20)

        #now we give each tab a name
        oTabWidget.addTab(oPage1,"Initialization")
        oTabWidget.addTab(oPage2,"Real-Time Data")
        oTabWidget.addTab(oPage3,"Data Manipulation")

        #this is a fairly complicated part, we give the main window a function which it will call every 2000 miliseconds, to refresh our graphs in the second tab
        self.anim = animation.FuncAnimation(oPage2.graph, oPage2.graph_plotter, interval = 2000)

        #finally, we give the command to actually show all the parts we inserted above on the main window
        self.show()


class Initialization(QMainWindow):
    def __init__(self):
        super().__init__()

        #each of the three classes derives from a "QMainWindow", which means it has a center widget, and some supporting widgets

        #first we create some simple labels
        self.template1 = QLabel("Calorimeter Port:")
        self.template2 = QLabel("Thermostat Port:")
        self.template3 = QLabel("Pump 1 Port:")
        self.template4 = QLabel("Pump 2 Port:")

        #then some lines where the user can write in
        self.name_1 = QLineEdit("COM6")
        self.name_2 = QLineEdit("COM10")
        self.name_3 = QLineEdit("COM13")
        self.name_4 = QLineEdit("COM14")
        
        self.template5 = QLabel("Operating Time:")
        self.template6 = QLabel("Dead Time:")
        self.template7 = QLabel("Pump 1 Name:")
        self.template8 = QLabel("Pump 2 Name:")
        
        self.name_5 = QLineEdit("20")
        self.name_6 = QLineEdit("10")
        self.name_7 = QLineEdit("Lambda 1")
        self.name_8 = QLineEdit("Lambda 2")

        #and finally some buttons which we connect to functions of this class
        self.start_opt = QPushButton("Start Recording")
        self.start_opt.clicked.connect(lambda:[self.data_thread()])

        self.start_test = QPushButton("Stop Recording")
        self.start_test.clicked.connect(stop_all_Threads)

        #now we make a widget with a specific height
        self.overall_main = QWidget()
        self.overall_main.setMaximumHeight(1250)

        #next we make a grid, with specific sizes
        self.overall_grid = QGridLayout(self.overall_main)
        self.overall_grid.setContentsMargins(40,40,40,40)
        self.overall_grid.setVerticalSpacing(10)

        #and now we put all the labels, lines and buttons from above in this grid
        self.overall_grid.addWidget(self.template1, 0,0)
        self.overall_grid.addWidget(self.template2, 0,1)
        self.overall_grid.addWidget(self.template3, 0,2)
        self.overall_grid.addWidget(self.template4, 0,3)

        self.overall_grid.addWidget(self.name_1, 1,0)
        self.overall_grid.addWidget(self.name_2, 1,1)
        self.overall_grid.addWidget(self.name_3, 1,2)
        self.overall_grid.addWidget(self.name_4, 1,3)
        
        self.overall_grid.addWidget(self.template5, 2,0)
        self.overall_grid.addWidget(self.template6, 2,1)
        self.overall_grid.addWidget(self.template7, 2,2)
        self.overall_grid.addWidget(self.template8, 2,3)
        
        self.overall_grid.addWidget(self.name_5, 3,0)
        self.overall_grid.addWidget(self.name_6, 3,1)
        self.overall_grid.addWidget(self.name_7, 3,2)
        self.overall_grid.addWidget(self.name_8, 3,3)

        self.overall_grid.addWidget(self.start_opt, 5,0)
        self.overall_grid.addWidget(self.start_test, 5,1)
        
        self.data_table = QTableWidget(10,5)
        for i in range(5):
            self.data_table.setColumnWidth(i,150)
        self.header_labels = ["0", "1", "2",
        "3", "4"]
        self.insert_in_table(number = 0, values = self.header_labels)
        
        self.overall_grid.addWidget(self.data_table, 6, 0, 10, 4)

        #and now we make this grid with all the stuff in in our main widget of the first tab
        self.setCentralWidget(self.overall_main)

        #we create a help text on the side of the tab
        self.helpWindow = QDockWidget()
        self.subwidget = QPlainTextEdit()
        self.text = open("Calorimetry\Help_Kal.txt").read()
        self.subwidget.setPlainText(self.text)
        self.subwidget.setReadOnly(True)

        self.helpWindow.setWidget(self.subwidget)
        self.addDockWidget(Qt.RightDockWidgetArea,self.helpWindow)

        #and we also make a menu bar with some actions in it, but they don't do anything yet
        self.menuBar = QMenuBar()
        self.menu = self.menuBar.addMenu("Menu")
        self.action1= QAction("Function 1", self.menu, checkable=True)
        self.action2= QAction("Function 2", self.menu, checkable=True)
        self.action3= QAction("Function 3", self.menu, checkable=True)
        self.menu.addAction(self.action1)
        self.menu.addAction(self.action2)
        self.menu.addAction(self.action3)

        self.setMenuBar(self.menuBar)

        #and finally we create a virtual excel sheet, that will take in our data
        self.book = openpyxl.Workbook()
        self.sheet = self.book.active
    
    def insert_in_table(cls,number, values):

        for i in range(len(values)):
            item = QTableWidgetItem()
            item.setText(str(values[i]))
            cls.data_table.setItem(number, (i), item)

    def data_thread(self):
        #this is the function that creates a thread which will take our data and put it in the excel sheet
        self.thread = Data_Thread(self, Initialization)
        self.thread.start()

    def datalogger(self):
        
        self.test_points()
        
    def test_points(self):
        # Betriebspunkte Liste
        val = 0.3*60*1E3
        val2 = 0.1*60*1E3
        operation_point_list = [
            Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
            Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
        ]
        
        # Stoffdaten
        self.substance_data = Strategy_OCAE.substance_data([4, 6], [50, 50], [40.01, 60.05], ["B", "A"])
        
        # Erstellen der Strategie
        self.strategy = Strategy_OCAE.Output_Calculation_Absolute_Evaluation(operation_point_list, self.substance_data, val2, "strategy_test")
        
        
        self.tmp_op = self.strategy.get_operation_point()
        
        new_point = True
        time_ = 5
        while self.tmp_op is not None:
            if new_point:
                print("new point")
                temperature = self.tmp_op.get_temperature()
                flowrate_list = []
                for i in range(self.tmp_op.get_number_of_pumps()):
                    flowrate_list.append(self.tmp_op.get_flowrate(i))
                self.strategy.push_actual_flowrate(flowrate_list)
                new_point = False
        
            self.value = [time_, temperature, temperature + 1.0, temperature + 0.9, temperature + 0.8,  temperature + 0.7, temperature + 0.6, temperature + 0.5, -4.0, -3.0, -1.0, 0.0, 0.0, 0.0]
            time_ += 2
        
            self.strategy.push_value(self.value)
            print(self.value)
        
            if self.strategy.has_error():
                raise Exception("error")
        
            if self.strategy.point_complete():
                new_point = True
                self.tmp_op = self.strategy.get_operation_point()
        
            time.sleep(2)
        self.strategy.get_finish_instruction()
        print("Done")
    
    def real_points(self):
        operating_time = 0.3*60*1E3
        dead_time = 0.1*60*1E3
        excel_file_name = "strategy_ocae"
        
        # List of operating points
        operation_point_list = [
            Strategy_OCAE.operation_point_list_entry(operating_time, 25, [6.1, 6.05]),
            Strategy_OCAE.operation_point_list_entry(operating_time, 25, [6.1, 6.05]),
            Strategy_OCAE.operation_point_list_entry(operating_time, 25, [6.1, 6.05]),
            Strategy_OCAE.operation_point_list_entry(operating_time, 25, [6.1, 6.05]),
        ]
        
        # Substance data 
        substance_data = Strategy_OCAE.substance_data([4, 6], [50, 50], [40.01, 60.05], ["B", "A"])
        
        # Devices used
        User_Pumps = [["Lambda 1", "COM12"], ["Lambda 3", "COM11"]] # [["HPLC A", "COM12"], ["HPLC B", "COM11"]] 
        User_Fisher = ["COM8"]
        Portname_Calorimeter = "COM6"
        
        # Setting up the strategy
        self.strategy = Strategy_OCAE.Output_Calculation_Absolute_Evaluation(operation_point_list, substance_data, dead_time, excel_file_name)
        
        # Setting up the automatization
        self.automat = Auto.matization(self.strategy, User_Pumps, User_Fisher, Portname_Calorimeter)
        
        # Automatization is called until the end state is reached
        while(True):
            self.automat.tick()
            if self.automat.get_state() == "Finished":
                break
            if self.automat.get_state() == "Error_Thermostat" or self.automat.get_state() == "Error_Pump" or self.automat.get_state() == "Error_Calorimeter" or self.automat.get_state() == "Error":
                break
        print("Done")

class Graph(QMainWindow):
    def __init__(self, instance):
        super().__init__()

        #this class is for the tab that should have our graphs in it

        self.instance = instance

        #first we create the figure with a specific size
        self.graph = Figure(figsize=(14,7), dpi=80)

        #then we create the 4 subplots that we put in the figure
        self.sub_graph_1 = self.graph.add_subplot(221)

        self.sub_graph_2 = self.graph.add_subplot(222)

        self.sub_graph_3 = self.graph.add_subplot(223)

        self.sub_graph_4 = self.graph.add_subplot(224)
        
        self.sub_graph_1.set_title("Reactor Temp")
        self.sub_graph_2.set_title("Inlet Temps")
        self.sub_graph_3.set_title("Voltage")
        self.sub_graph_4.set_title("PWM")
        
        self.values = [[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
    
        self.max_excel_row = 0

        #now we put the figure into a canvas that we can insert into our actual GUI window
        self.canvas = FigureCanvasQTAgg(self.graph)

        #and we set this canvas as the main widget of the second tab
        self.setCentralWidget(self.canvas)

        #as for the first tab, we create a help text on the side, and a menu at the top
        self.helpWindow = QDockWidget()
        self.subwidget = QPlainTextEdit()
        self.text = open("Calorimetry\Help_Data.txt").read()
        self.subwidget.setPlainText(self.text)
        self.subwidget.setReadOnly(True)

        self.helpWindow.setWidget(self.subwidget)
        self.addDockWidget(Qt.RightDockWidgetArea,self.helpWindow)

        self.menuBar = QMenuBar()
        self.menu = self.menuBar.addMenu("Menu")
        self.action1= QAction("Function 1", self.menu, checkable=True)
        self.action2= QAction("Function 2", self.menu, checkable=True)
        self.action3= QAction("Function 3", self.menu, checkable=True)
        self.menu.addAction(self.action1)
        self.menu.addAction(self.action2)
        self.menu.addAction(self.action3)

        self.setMenuBar(self.menuBar)

        #and we also make a toolbar to be able to manipulate the graphs a little bit
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        self.addToolBar(self.toolbar)


    def graph_plotter(self, buffer_var):
        #this is the function that takes the excel sheet from the first tabs, and plots the data in it in our 4 subplots
        sheet_1 = self.instance.sheet
        
        counter = 0
        for i in self.values:
            try:
                i.append(self.instance.value[counter])
                counter += 1
            except:
                pass
        
        self.sub_graph_1.clear()
        self.sub_graph_2.clear()
        self.sub_graph_3.clear()
        self.sub_graph_4.clear()
        
        
        #and then we plot our new values into the empty graphs
        for x in (self.values[1], self.values[2], self.values[3], self.values[4]):
            self.sub_graph_1.plot(self.values[0], x)

        for x in (self.values[8], self.values[9], self.values[10]):
            self.sub_graph_2.plot(self.values[0], x)

        for x in (self.values[11], self.values[12], self.values[13],self.values[14]):
            self.sub_graph_3.plot(self.values[0], x)

        for x in (self.values[18], self.values[19],self.values[20]):
            self.sub_graph_4.plot(self.values[0], x)


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


#------------------------------------------------------------------------------
#now that we have all the needed classes, we actually create an opbject out of them

app = QApplication([])
app.setStyle("Fusion")

palette = QPalette()
palette.setColor(QPalette.ButtonText, Qt.black)
app.setPalette(palette)

#this is the main object, which includes basically all the code from above
Main = TopLevelWindow()

app.exec_()