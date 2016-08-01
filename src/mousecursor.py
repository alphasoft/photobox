#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, syslog
# TODO: set this path via configure or something similar.
sys.path.append('/usr/local/lib/python2.4/site-packages/libavg')
import avg

def onMouseMove():
    Event = Player.getCurEvent()
    MouseCursor = Player.getElementByID("mousecursor")
    MouseCursor.x = Event.x-16
    MouseCursor.y = Event.y-16

def onMouseDown():
    print "Click" 

Player = avg.Player()
Player.loadFile("mousecursor.avg")
Player.showCursor(False)
Player.setVBlankFramerate(1)
Player.play()

