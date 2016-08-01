#! /usr/bin/python

import sys, os, time
sys.path.append('/usr/local/lib/python2.4/site-packages/libavg')
import avg

theLog = avg.Logger.get()
theLog.setCategories(theLog.APP                |
                     theLog.WARNING            |
#                     theLog.PROFILE            |
#                     theLog.PROFILE_LATEFRAMES |
                     theLog.CONFIG             |
                     theLog.MEMORY             |
#                     theLog.BLTS               |
                     theLog.EVENTS)

thePlayer = avg.Player()
theCamera = None

flipped = False

def printWB():
    uBlue = theCamera.whitebalance / 256
    vRed =  theCamera.whitebalance % 256
    print "White balance: u/blue: " + str(uBlue) + ", v/red: " + str(vRed) + " (" + str(theCamera.whitebalance) + ")"

def keyPressed():
    global flipped
    key = thePlayer.getCurEvent().keystring
    if key == "q":
	sys.exit()
    if key == "space":
        theCamera.getBitmap().save("snapshot.png")
    if key == "enter":
        printWB()
    if key == "[+]":
        theCamera.whitebalance = theCamera.whitebalance + 1
        printWB()
    if key == "[-]":
        theCamera.whitebalance = theCamera.whitebalance - 1
        printWB()
    if key == "[*]":
        theCamera.whitebalance = theCamera.whitebalance + 256
        printWB()
    if key == "[/]":
        theCamera.whitebalance = theCamera.whitebalance - 256
        printWB()
    if key == "[0]":
        theCamera.whitebalance = -1
        printWB()
    if key == "right":
	flip(False)
    if key == "left":
	flip()
    if key == "print screen":
	flip(flipped)
    print key

def flip(really = True):
	global flipped
	flipped = not really
	for y in range(theCamera.getNumVerticesY()):
	    for x in range(theCamera.getNumVerticesX()):
		pos = theCamera.getOrigVertexCoord(x, y)
		if really:
		    pos.x = 1 - pos.x
		theCamera.setWarpedVertexCoord(x, y, pos)

thePlayer.setDisplayEngine(avg.OGL)
thePlayer.setResolution(0, 0, 0, 24)
thePlayer.loadFile("cam.avg")

theCamera = thePlayer.getElementByID("camera")
print("Vertices: " + str(theCamera.getNumVerticesX()) + "x" + str(theCamera.getNumVerticesY()))
theCamera.play()

thePlayer.setTimeout(1000, flip)
os.system("sleep 2")
thePlayer.play()

