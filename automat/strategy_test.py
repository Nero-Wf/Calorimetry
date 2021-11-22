import automat.Strategy_OCAE as Strategy_OCAE
import time

def test_points():
    # Betriebspunkte Liste
    val = 0.3*60*1E3
    val2 = 0.1*60*1E3
    operation_point_list = [
        Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
        Strategy_OCAE.operation_point_list_entry(val, 25, [6.1, 6.05]),
    ]
    
    # Stoffdaten
    substance_data = Strategy_OCAE.substance_data([4, 6], [50, 50], [40.01, 60.05], ["B", "A"])
    
    # Erstellen der Strategie
    strategy = Strategy_OCAE.Output_Calculation_Absolute_Evaluation(operation_point_list, substance_data, val2, "strategy_test")
    
    
    
    tmp_op = strategy.get_operation_point()
    
    new_point = True
    time_ = 5
    while tmp_op is not None:
        if new_point:
            print("new point")
            temperature = tmp_op.get_temperature()
            flowrate_list = []
            for i in range(tmp_op.get_number_of_pumps()):
                flowrate_list.append(tmp_op.get_flowrate(i))
            strategy.push_actual_flowrate(flowrate_list)
            new_point = False
    
        value = [time_, temperature, temperature + 1.0, temperature + 0.9, temperature + 0.8,  temperature + 0.7, temperature + 0.6, temperature + 0.5, -4.0, -3.0, -1.0, 0.0, 0.0, 0.0]
        time_ += 2
    
        strategy.push_value(value)
        print(value)
    
        if strategy.has_error():
            raise Exception("error")
    
        if strategy.point_complete():
            new_point = True
            tmp_op = strategy.get_operation_point()
    
        time.sleep(2)
    strategy.get_finish_instruction()
    print("Done")
    
