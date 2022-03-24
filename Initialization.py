#first we import all the modules needed for this script
from PySide6.QtCore import *
from PySide6.QtWidgets import QWidget, QMainWindow, QGridLayout, QLineEdit, QLabel, QPushButton, QDockWidget, QTableWidget, QPlainTextEdit, QMenuBar, QTableWidgetItem
from PySide6.QtGui import QAction

from openpyxl import load_workbook


import time

import automat.Calorimeter as Calorimeter
import automat.Auto as Auto
import automat.Strategy_OCAE as Strategy_OCAE

from Data_Processing import Data_Thread

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
        
        self.data_table = QTableWidget(10,4)
        for i in range(4):
            self.data_table.setColumnWidth(i,150)
        self.header_labels = ["Operating time [s]", "Temperature [°C]", "Flowrate 1 [mL/min]", "Flowrate 2 [mL/min]"]
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

        self.point_finished_list = []

    
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
        #val = 0.3*60*1E3
        #val2 = 0.1*60*1E3
        
        val2 = float(self.name_6.text())*1E3


        #operation_point_list = [
        #    Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
        #    Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
        #]
        
        rowdata = []
        for row in range(self.data_table.rowCount()):
                    for column in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                            print(item.text())
                        else:
                            break
        
        # List of operating points
        operation_point_list = []

        point_number = len(rowdata) // 4
        print(point_number)

        for i in range(0,(point_number*4-4),4):
            op_time = float(rowdata[i+4]) * 1E3
            temperature = float(rowdata[i+5])
            flowrate1 = float(rowdata[i+6])
            flowrate2 = float(rowdata[i+7])
            operation_point_list.append(Strategy_OCAE.operation_point_list_entry(op_time, temperature, [flowrate1, flowrate2]))

        print("Number of points: ", len(operation_point_list))
        
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

                try:
                    self.point_finished_list.append(self.strategy.datalist[-1][0])
                except:
                    print("no point recorded yet")

            self.value = [time_, temperature, temperature + 1.0, temperature + 0.9, temperature + 0.8,  temperature + 0.7, temperature + 0.6, temperature + 0.5, temperature + 0.5, temperature + 0.5, temperature + 0.5, -4.0, -3.0, -1.0, 0.0, 0.0, 0.0, -4.0, -3.0, -1.0, 0.0, 0.0, 0.0, -4.0, -3.0, -1.0, 0.0, 0.0, 0.0]
            time_ += 2
        
            self.strategy.push_value(self.value)
            print(self.value)
        
            if self.strategy.has_error():
                raise Exception("error")
        
            if self.strategy.point_complete():
                new_point = True
                self.tmp_op = self.strategy.get_operation_point()
        
            time.sleep(1)
        self.strategy.get_finish_instruction()
        print("Done")
    
    def real_points(self):
        #operating_time = 0.3*60*1E3
        #dead_time = 0.1*60*1E3
        
        dead_time = float(self.name_6.text())*1E3

        excel_file_name = "strategy_ocae"
        
        rowdata = []
        for row in range(self.data_table.rowCount()):
                    for column in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                            print(item.text())
                        else:
                            break
        
        # List of operating points
        operation_point_list = []

        point_number = len(rowdata) // 4
        print(point_number)

        for i in range(0,(point_number*4-4),4):
            op_time = float(rowdata[i+4]) * 1E3
            temperature = float(rowdata[i+5])
            flowrate1 = float(rowdata[i+6])
            flowrate2 = float(rowdata[i+7])
            operation_point_list.append(Strategy_OCAE.operation_point_list_entry(op_time, temperature, [flowrate1, flowrate2]))

        print("Number of points: ", len(operation_point_list))

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

def stop_all_Threads():
    """function to stop all threads via the stop command"""
    #we first declare this variable to be a global variable, and then set it to true.
    #this stops the loop of the thread.
    global stop_threads
    stop_threads = True
    print("all Threads stopped")