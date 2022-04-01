#first we import all the modules needed for this script
from PySide6.QtCore import *
from PySide6.QtWidgets import QMainWindow, QDockWidget, QPlainTextEdit, QMenuBar
from PySide6.QtGui import QAction


from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT


class Graph(QMainWindow):
    def __init__(self, instance):
        super().__init__()

        #this class is for the tab that should have our graphs in it

        #we also need to know the initialization graph instance, so we can get the data from it 
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
        
        self.values = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
        self.new_point_list = []

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
    
    def real_time_plotter(self, buffer):
        #this is the function that plots the data from the equipment in real time

        self.sub_graph_1.clear()
        self.sub_graph_2.clear()
        self.sub_graph_3.clear()
        self.sub_graph_4.clear()

        self.values = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]

        self.sub_graph_1.set_title("Reactor Temp")
        self.sub_graph_2.set_title("Inlet Temps")
        self.sub_graph_3.set_title("Voltage")
        self.sub_graph_4.set_title("PWM")

        try:
            for i in self.instance.strategy.datalist:
                for j in range(len(self.values)):
                    self.values[j].append(i[j])

            #and then we plot our new values into the empty graphs
              
            self.sub_graph_1.plot(self.values[0], self.values[1], label = "t_set")
            self.sub_graph_1.plot(self.values[0], self.values[2], label = "t_pre")
            self.sub_graph_1.plot(self.values[0], self.values[8], label = "t_A")
            self.sub_graph_1.plot(self.values[0], self.values[9], label = "t_B")
            self.sub_graph_1.plot(self.values[0], self.values[10], label = "t_out")
            self.sub_graph_1.legend(loc=1)
            
            self.sub_graph_2.plot(self.values[0], self.values[1], label = "t_set")
            self.sub_graph_2.plot(self.values[0], self.values[3], label = "t_r1")
            self.sub_graph_2.plot(self.values[0], self.values[4], label = "t_r2")
            self.sub_graph_2.plot(self.values[0], self.values[5], label = "t_r3")
            self.sub_graph_2.plot(self.values[0], self.values[6], label = "t_r4")
            self.sub_graph_2.plot(self.values[0], self.values[7], label = "t_r5")
            self.sub_graph_2.legend(loc=1)
            
            self.sub_graph_3.plot(self.values[0], self.values[11], label = "U_pre")
            self.sub_graph_3.plot(self.values[0], self.values[12], label = "U_r1")
            self.sub_graph_3.plot(self.values[0], self.values[13], label = "U_r2")
            self.sub_graph_3.plot(self.values[0], self.values[14], label = "U_r3")
            self.sub_graph_3.plot(self.values[0], self.values[15], label = "U_r4")
            self.sub_graph_3.plot(self.values[0], self.values[16], label = "U_r5")
            self.sub_graph_3.legend(loc=1)

            
            self.sub_graph_4.plot(self.values[0], self.values[17], label = "PWM_pre")
            self.sub_graph_4.plot(self.values[0], self.values[18], label = "PWM_r1")
            self.sub_graph_4.plot(self.values[0], self.values[19], label = "PWM_r2")
            self.sub_graph_4.plot(self.values[0], self.values[20], label = "PWM_r3")
            self.sub_graph_4.plot(self.values[0], self.values[21], label = "PWM_r4")
            self.sub_graph_4.plot(self.values[0], self.values[22], label = "PWM_r5")
            self.sub_graph_4.legend(loc=1)

        except:
            pass

        try:
            for i in self.instance.point_finished_list:
                self.sub_graph_1.axvline(x=i, color='r')
                self.sub_graph_2.axvline(x=i, color='r')
                self.sub_graph_3.axvline(x=i, color='r')
                self.sub_graph_4.axvline(x=i, color='r')
        except:
            pass
