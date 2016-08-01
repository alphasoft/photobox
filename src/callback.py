#!/usr/bin/python
# -*- coding: utf-8 -*-

class AVGCallback:
    """
   Manage a single timeout and a single interval sunction.
   AVGCallback.setInterval has  the same signature as the avg counterpart, but _replaces_ the old interval function instead of adding a new one.
   
   Same with timeout

   """
   def __init__(self,player,name="default"):
       self.player=player
       self.timeout_set = False
       self.interval_set = False
       self.timout_id = None
       self.interval_id = None
   def __repr__(self):
      return "%s: interval:%s  timeout: %s" %(self.name,self.interval_set,self.timeout_set)
   def setInterval(self,callback,delta_t):
      """Replace the callback handled by this instance with another one
      """
      if self.interval_set:
         self.player.clearInterval(self.interval_id)
      self.interval_id=self.player.setInterval(callback,delta_t)
      self.interval_set = True
   def setTimeout(self,callback,timeout):
      """Replace the timeout function handled by this instance with another one
      """
       if self.timeout_set:
         self.player.clearInterval(self.interval_id)
      self.timeout_id=self.player.setTimeout(callback,timeout)
      self.timeout_set = True
   def cancelTimeout(self):
      if self.timeout_set:
         self.player.clearInterval(self.timeout_id)
         self.timeout_set=False
   def clearInterval(self):
      if self.inteval_set:
         self.player.clearInterval(self.interval_id)
   def __del__(self):
      self.clearInterval()
      self.cancelTimeout()


class CountDown:
   def __init__(self,player,timeout,counting_f,finished_f):
      assert(timeout>0)
      self._timeout=self._counter=timeout
      self.avg_id=None
      self.counting_f=counting_f
      self.finished_f=finished_f
   def _getCounter(self):
      return self._counter
   counter=property(_getCounter)
   def __call__(self):
      self._counter-=1
      self.counting_f(self.player,self._counter)
      if self._counter==0:
         self.finished_f(player)
         self.stop()
      assert(self._counter>=0)
   def start(self):
      self._counter=self._timeout
      self.avg_id=player.setTimeout(self,1000)
   def stop(self):
      if self.avg_id:
         player.clearInterval(self.avg_id)
         self.avg_id=None

