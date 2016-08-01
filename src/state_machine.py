class FSM:
    def __init__(self,blob=None):
        self.state_transitions={}
        self.current_state=None
        self.blob=blob
        self.default_transition={}
        
    def add_state(self,state):
        self.state_transitions[state]={}
        self.default_transition[state]={}
        
    def add_transition(self,initial_state,event,action,new_state):
        self.state_transitions[initial_state][event]=(action,new_state)
    def add_default_transition(self,initial_state,action,new_state):
        self.default_transition[state]=(action,new_state)
    def event(self,event):
        trans=self.state_transitions[self.current_state]
        try:
            action,new_state=trans[event]
        except KeyError:
            try:
                action,new_state=self.default_transition[self.current_state]
            except KeyError:
                raise KeyError("Event %s not found in state %s"%(event,self.current_state))
        action(self.blob)
        self.current_state=new_state
    def start(self,start_state):
        self.current_state=start_state


def gotoScreen(scrname):
    print "Changing screen to %s"%scrname
    
def setupMotif(stuff):
    gotoScreen("selectingMotif")

def setupScrSvr(stuff):
    gotoScreen("ScrSvr")    

if __name__=="__main__":

    machine=FSM()
    machine.add_state("ScreenSaver")
    machine.add_state("SelectMotif")
    machine.add_transition("ScreenSaver","click",action=setupMotif,new_state="SelectMotif")
    machine.add_transition("SelectMotif","timeout",action=setupScrSvr,new_state="ScreenSaver")
    machine.start("ScreenSaver")
    def onMousedown():
        machine.event("mousedown")
            
    machine.event("timeout")
    machine.event("dummes")
