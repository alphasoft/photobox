#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
     +---------------+
+----+  camtest.py   +--------------------+
|    +---------------+                    | 
|                                         |
+-----------------------------------------+
"""
      
import sys, os, time
sys.path.append('/usr/local/lib/python2.4/site-packages/libavg')
import avg

# AVG globale Variablen
log = avg.Logger.get()
pl  = avg.Player()  # thePlayer
cam = avg.Camera()  # theCamera
avgFile = "camera_test.avg"

pl.setDisplayEngine(avg.OGL)
pl.setResolution(0,1280,1024,24)
pl.showCursor(1) 
pl.loadFile(avgFile)

pl.play()
pl.getElementByID('camera').play
