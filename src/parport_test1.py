#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, math, time
sys.path.append('/usr/local/lib/python2.4/site-packages/libavg')
import avg

# pl=avg.Player()



parPort = avg.ParPort()
parPort.init("/dev/parport0")

bit0 = avg.Datalines.PARPORTDATA0
bit1 = avg.Datalines.PARPORTDATA1

if parPort.isAvailable:
  print "OK - Port erkannt."
else:
  print "Parport ??"

parPort.getControlLines(ACK)
parPort.setAllDataLines(False)

parPort.setDataLines(bit0,1)