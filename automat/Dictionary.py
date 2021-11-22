# This file contains general settings and values that do not have to be
# changed every time the programme is run, but it is still convenient to
# be able to change these values.

# own scripts:
import automat.Calibration as Calibration

pump_calibration = {
    "HPLC A": Calibration.Pumps(1000),
    "HPLC B": Calibration.Pumps(1000),
    "HPLC C": Calibration.Pumps(1000),
    "Lambda 1": Calibration.Pumps(20.117),
    "Lambda 2": Calibration.Pumps(80.265),
    "Lambda 3": Calibration.Pumps(20.294),
    }

calorimeter_thermostat = {
    "calibration": Calibration.Thermostat(25, 40, [[25,26], [30, 34], [35, 40]]),
    "25": Calibration.Calorimeter([[1,2,3], [1,2,3], [1,2,3]]),
    }

pump_head = {
    "HPLC A": 50,
    "HPLC B": 50,
    "HPLC C": 10,
    }

lambda_address = {
    "Lambda 1": 2,
    "Lambda 2": 2,
    "Lambda 3": 2,
    }

calculation_data = {
    "concentration": 0.997/18.015*1000,       # mol/l
    "cp": 75.336,                             # J/(molK)
    }
