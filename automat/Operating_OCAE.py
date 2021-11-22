import Auto
import Strategy_OCAE

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
strategy = Strategy_OCAE.Output_Calculation_Absolute_Evaluation(operation_point_list, substance_data, dead_time, excel_file_name)

# Setting up the automatization
automat = Auto.matization(strategy, User_Pumps, User_Fisher, Portname_Calorimeter)

# Automatization is called until the end state is reached
while(True):
    automat.tick()
    if automat.get_state() == "Finished":
        break
    if automat.get_state() == "Error_Thermostat" or automat.get_state() == "Error_Pump" or automat.get_state() == "Error_Calorimeter" or automat.get_state() == "Error":
        break
print("Done")
