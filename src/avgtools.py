"""
   Helper classes for using AVG callbacks and timer functionality more safely
   idea and code by Igor
"""


#make new-style classes the default. http://www.python.org/download/releases/2.2.3/descrintro/
__metaclass__ = type

_registry = {}


def stop_all():
   for inst in _registry.values():
     inst.stop()
   for k in _registry.keys():
     del _registry[k]

class AVGCallback:
   """
  Manage a single interval function, signature : func()
  AVGCallback encapsulates the setting and clearing of avg.Player.setInterval
  functions with its methods start and stop.

  It is safe to call start and stop repeatedly.
  """
   def __init__(self, player, f, delta_t, name="default"):
      self.player = player
      self.delta_t = delta_t
      self.f = f
      self.interval_id = None
      self.name = name
   def __repr__(self):
      return "%s calls %s every %s ms" % (self.name, self.f.func_name, self.delta_t)
   def start(self):
      if self.interval_id == None:
         _registry[id(self)]=self
         self.interval_id = self.player.setInterval(self.delta_t, self.f)
   def stop(self):
      if self.interval_id != None:
         self.player.clearInterval(self.interval_id)
         self.interval_id = None
         del _registry[id(self)]
   def __del__(self):
      self.stop()
# end of AVGCallback class.

class SelfTerminatingCallback(AVGCallback):
    """ Use the given function as a periodically called function that my
    request its termination by raising an(any) exception. 
    
    Then an optional finalising function final_f() gets called
    """
    def __init__(self, player, f, final_f, delta_t, name="default"):
        self.final_f = final_f
        def inner():
            """Behold the power of closures"""
            try:
                f()
            except:
                self.stop()
                if callable(self.final_f):
                    self.final_f()
        inner.__name__ = "wrapped_"+f.__name__   
        super(SelfTerminatingCallback,self).__init__(player,inner,delta_t,name)
        

class CountDown:
   """ Manage calls to a counting function at given rate and finish by calling a
       finalizer function ( signature : func(pl) ).

       If timestep is not given a step of 1s is assumed.
       
   """
   def __init__(self, player, timeout, counting_f = None, finished_f = None,
                               timestep=1000,name="default", display=False):
      assert(timeout > 0)
      self.name = name
      self.player = player
      self._timeout = self._counter = timeout
      self._hasDisplay = display
      self.avg_id = None
      displayShow = ""
      if self._hasDisplay:
        displayShow = "- showing Timeout display!"
      print "%s sec countdown registered as %s %s" % (str(timeout), self.name, displayShow)
      if not counting_f:
          self.counting_f = self.tick
      else:
          self.counting_f = counting_f
      if not finished_f:
          self.finished_f = lambda pl:None
      else:
          self.finished_f = finished_f
      self.timestep = timestep
      self.running = False

   def _getCounter(self):
      return self._counter
   counter = property(_getCounter)

   def tick(self, pl, counter):
      print "[ %s: %s s ]" % (self.name, str(counter))
      if self._hasDisplay:
        if counter == self._timeout/2:
          self.displayCounter(counter)
        if counter <= self._timeout/2 and counter >= 0:
          self.player.getElementByID(self.name+"_sec").text = str(counter) # update counter

   def __call__(self):
      self._counter -= 1
      self.counting_f(self.player, self._counter)
      if self._counter == 0:
         if self._hasDisplay:  #  instruktiver: if self._hasShownUp==True:
            self.hideCounter()
         print "Countdown [%s] ran out: %s()" %( self.name, self.finished_f.func_name)
         self.stop()
         self.finished_f(self.player)
      if self._counter<0:
         self.__del__()

   def start(self):
      """ Calling start on an already running countdown does nothing.
          To reset, call stop, then start again
      """
      self.running = True
      print "CountDown [%s] started, %s steps"%(self.name,self._timeout)
      if self.avg_id == None: # no callback set until now
         self._counter = self._timeout
         if self.counting_f != None:
            self.avg_id = self.player.setInterval(self.timestep, self)
         else:
            self.avg_id = self.player.setTimeout(self._timeout*self.timestep, 
                    self.finished_f)

   def stop(self):
      self.running = False
      if self.avg_id != None:
         print "CountDown [%s] stopped." % self.name
         if self._hasDisplay:
            self.hideCounter()
         self.player.clearInterval(self.avg_id)
         self.avg_id = None

   def displayCounter(self,counter):
      if self._hasDisplay:
        print "[[..showing overlay..]]"
        self.player.getElementByID(self.name+"_ovl").opacity = 1
        self.player.getElementByID(self.name+"_sec").opacity = 1
        self.player.getElementByID(self.name+"_sec").text = str(counter)
        self.player.getElementByID(self.name+"_hint_de").opacity = 1
        self.player.getElementByID(self.name+"_hint_en").opacity = 1

   def hideCounter(self):
      if self._hasDisplay:
        print "[[..hiding overlay..]]"
        self.player.getElementByID(self.name+"_sec").opacity = 0
        self.player.getElementByID(self.name+"_ovl").opacity = 0
        self.player.getElementByID(self.name+"_hint_de").opacity = 0
        self.player.getElementByID(self.name+"_hint_en").opacity = 0

   def __del__(self):
      self.stop()

# end of CountDown class.
