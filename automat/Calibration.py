class Pumps:
    def __init__(self, cali_val):
        self.cali_val = cali_val        

    def __call__(self, value):
        return value * self.cali_val

    def forward(self, value):
        return value * self.cali_val

    def backward(self, value):
        return value/self.cali_val

class Thermostat:
    """This class ensures that the correct temperature is selected at the thermostat for a given set temperature of the calorimeter."""
    def __init__(self, lower_limit, upper_limit, list):     
        self.list = sorted(list, key=lambda entry: entry[0])
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit

    def forward(self, value):
        if value < self.lower_limit:
            raise Exception("Calorimeter set temperature is too low")
        if not value <= self.upper_limit:
            raise Exception("Calorimeter set temperature is too high")

        for itm in self.list:
            if value <= itm[0]:
                return itm[1]

        raise Exception("Given set temperature is above the given calibration table")

class Calorimeter:
    def __init__(self, list):
       self.list = list
       if not len(self.list) == 3:
           raise Exception("Given parameter list is incomplete")

    def forward(self, value_list):
        tmp = []

        if not len(value_list) == 3:
           raise Exception("Given evaluation data list is incomplete")
        
        for idx in range(3):
            tmp.append((self.list[idx][0]*value_list[idx]*value_list[idx]+self.list[idx][1]*value_list[idx]+self.list[idx][2])*(-1))

        return tmp
