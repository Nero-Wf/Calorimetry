# This file contains the basic class for creating a state, from which 
# all further states inherit later, and the engine class that is 
# responsible for building (This is done via the factory) and running 
# the states, which is always called in the state machine.

class State_Base:
    
    def enter(self, name):
        self.name = name
        # print("entering state --- {}".format(self.name))
  
    def __call__(self):
        return None
    
    def exit(self):
        # print("exiting state --- {}".format(self.name))
        return

    def handle_event(self, event):
        return False

    def get_state(self):
        return self.name

class Engine:
    
    def __init__(self,  table, factory, init_state):
        self.tab = table
        self.fac = factory
        self.init_state = init_state
        self.cur = None

    def enter(self):
        self.cur = self.fac.create_state(self.init_state)

        if self.cur is None:
            raise Exception("Factory has created None")
    
    def __del__(self):
        self.exit()
    
    def exit(self):
        if self.cur is not None:
            self.cur.exit()
            self.cur = None

    def search_in_table(self, event):
        for tran in self.tab:
            if not tran[0] == self.cur.get_state():
                continue
            if not tran[1] == event:
                continue

            self.cur.exit()
            self.cur = self.fac.create_state(tran[2])
            return True
        return False
 
    def tick(self):
        ent = self.cur()
        if ent is None:
            return None
        if self.search_in_table(ent):
            return None
        return ent
    
    def handle_event(self, event):
        if self.search_in_table(event):
            return True
        if self.cur.handle_event(event):
            return True
        return False
        
    def get_state(self):
        return self.cur.get_state()



