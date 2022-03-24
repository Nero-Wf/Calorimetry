#first we import all the modules needed for this script
from PySide6.QtCore import *
from PySide6.QtWidgets import QTabWidget, QWidget, QApplication
from PySide6.QtGui import QPalette

import matplotlib.animation as animation

from Initialization import Initialization
from Graph_Window import Graph
from Data_Processing import Data_Processing


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
        self.anim = animation.FuncAnimation(oPage2.graph, oPage2.real_time_plotter, interval = 2000)

        #finally, we give the command to actually show all the parts we inserted above on the main window
        self.show()


def stop_all_Threads():
    """function to stop all threads via the stop command"""
    #we first declare this variable to be a global variable, and then set it to true.
    #this stops the loop of the thread.
    global stop_threads
    stop_threads = True
    print("all Threads stopped")


#------------------------------------------------------------------------------
#now that we have all the needed classes, we actually create an opbject out of them
def main():
    app = QApplication([])
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ButtonText, Qt.black)
    app.setPalette(palette)

    #this is the main object, which includes basically all the code from above
    Main = TopLevelWindow()

    app.exec()

if __name__ == "__main__":
    main()
    stop_all_Threads()