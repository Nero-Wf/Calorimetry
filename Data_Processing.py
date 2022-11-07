#first we import all the modules needed for this script

import csv
import os
import threading

import pandas as pd
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QMainWindow, QMenuBar,
                               QTableWidget, QTableWidgetItem, QWidget)


class Data_Processing(QMainWindow):
    """overall class to manage the optimization point history"""
    def __init__(self):
        super().__init__()

        self.data_table = QTableWidget(3000,29)
        #self.data_table.setColumnWidth(0,120)
        #self.data_table.setColumnWidth(1,120)
        #self.data_table.setColumnWidth(2,120)
        #self.data_table.setColumnWidth(3,120)
        #self.data_table.setColumnWidth(4,120)
        #self.data_table.setColumnWidth(5,120)
        #self.data_table.setColumnWidth(6,120)
        #self.data_table.setColumnWidth(7,120)
        #self.data_table.setColumnWidth(8,120)
        #self.data_table.setColumnWidth(9,120)
        #self.data_table.setColumnWidth(10,120)

        self.menuBar = QMenuBar()
        self.menu = self.menuBar.addMenu("Menu")
        action1 = self.menu.addAction("Save Text")
        action2 = self.menu.addAction("Save Table")
        action3 = self.menu.addAction("Load Output")

        action1.triggered.connect(self.save)
        action2.triggered.connect(self.save_table)
        action3.triggered.connect(self.loadExcelData)

        self.setMenuBar(self.menuBar)

        self.overall_main = QWidget()

        self.overall_grid = QGridLayout(self.overall_main)

        self.overall_grid.addWidget(self.data_table, 0,0)

        self.setCentralWidget(self.overall_main)


    def loadExcelData(self):
        
        brush = QBrush("lightGray")

        df = pd.read_excel("Calorimetry\strategy_test.xlsx", engine='openpyxl')
        if df.size == 0:
            return

        df.fillna('', inplace=True)
        self.data_table.setRowCount(df.shape[0])
        self.data_table.setColumnCount(df.shape[1])
        self.data_table.setHorizontalHeaderLabels(df.columns)

        # returns pandas array object
        for row in df.iterrows():
            values = row[1]
            for col_index, value in enumerate(values):
                tableItem = QTableWidgetItem()
                if isinstance(value, (str)):
                    if value is not "":
                        tableItem.setBackground(brush)
                if isinstance(value, (float, int)):
                    value = '{0:0,.2f}'.format(value)
                tableItem.setText(str(value))

                self.data_table.setItem(row[0], col_index, tableItem)


    def save(self):
        """
        saves the text in the text widget to a txt file
        """

        S__File = QFileDialog.getSaveFileName(None,'SaveTextFile','/', "Text Files (*.txt)")

        Text = self.txt_edit.toPlainText()

        if S__File[0]:
            with open(S__File[0], 'w') as file:
                file.write(Text)

    def save_table(self):
        """
        saves the content of the table widget to a csv file
        """
        path = QFileDialog.getSaveFileName(None, 'Save File', '', 'CSV(*.csv)')

        if path[0]:
            with open(path[0], 'w', newline='') as stream:
                writer = csv.writer(stream)
                for row in range(self.data_table.rowCount()):
                    rowdata = []
                    for column in range(self.data_table.columnCount()):
                        item = self.data_table.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

    def save_table_automated(self, algorithm, function):
        """
        saves the content of the table widget to a csv file
        """
        file_name = str(function)+str(".csv")
        with open(file_name, 'a+', newline='') as stream:
            writer = csv.writer(stream)
            for row in range(self.data_table.rowCount()):
                rowdata = []
                for column in range((self.data_table.columnCount()-3)):
                    item = self.data_table.item(row, column)
                    if item is not None:
                        rowdata.append(item.text())
                    else:
                        rowdata.append('')
                writer.writerow(rowdata)


    def write_in(cls, text):
        """
        function to insert given text into the text widget
        """
        cls.txt_edit.insertPlainText(text)

    def insert_in_table(self, cls, number: int, values):

        for i in range(len(values)):
            item = QTableWidgetItem()
            item.setText(str(values[i]))
            cls.data_table.setItem(number, (i), item)

    def open_csv(self):
        """
        for this, put a csv file with the needed values into the modules folder and the overall folder
        """

        current_directory = os.path.dirname(os.path.realpath(__file__))
        #current_directory = current_directory[:-7]
        print(current_directory)

        for root, dirs, files in os.walk(current_directory):
            for filename in files:
                if str(filename[-4:]) == ".csv":
                    path = filename

        path = str(path)
        print(path)

        with open(path, mode = "r") as csv_file:

            csv_reader = csv.DictReader(csv_file)
            line_count = 1

            for row in csv_reader:
                parameters = [row.get("Exp Nr"), row.get("Temperature"), row.get("Residence Time"),
                row.get("Substrate Ratio"), row.get("Yield"), row.get("Error Value") , row.get("Experiment Time"), row.get("Real Ratio")]
                print(parameters)
                self.insert_in_table(number =line_count, values =parameters)
                line_count +=1

            print("History imported")

