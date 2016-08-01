#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
     +---------------+
+----+  Photobox.py  +----------------------+
|    +---------------+                      |
|                                           |
|        Zentrale Ablaufsteuerung           |
|        des Photobox-Automaten             |
|        Entwickler : Alexander Lenz, Igor  |
|                     u. Christian Herrmann |
+----------------------+------------+-------+
                       +  V.0.16.2  +
                       +  21-04-06  +
                       +------------+

    MAC-VERSION
    Ohne Velleman (nur Simulation=True) u. ohne Camera 
"""

import sys, os, math, time
sys.path.append('/usr/local/lib/python2.4/site-packages/libavg')
import avg
from avgtools import *

# AVG globale Variablen
avgFile = "pb_screens.avg"  # Steuerdatei (Bildschirminhalte, Input)
Log = avg.Logger.get()     # Logger mit Datestamp
Log.setCategories(Log.WARNING)  # (Log.PROFILE | ..)  Profile statistics

thePlayer = avg.Player()  # zentrale Abspielinstanz

# Constanten
pl=thePlayer       # nur als Abk.
numTemplates = 5   # wieviele Postkartenmotive
numSnapshots = 4   # Fünf Bilder vom Besucher
photoPath = "../output/"
motivPath = "../media/"
ourCamera = None    # Objekt der eigenen Klasse Camera (s.u.)

# Globale Variablen, Handles u. Namenslisten für den Programmablauf
simulation = False
coinsIn = 0        # Hat Münzeinwurf stattgefunden ?
flashing = 0       # Während des Blitzens ist dieses Callback aktiv
zoom = 0           # hineinzoomen ins gewählte Motiv auf Kopfbereich
scrSaver = 0
switchOnOff = None
photoFile = ["snapshot_01.bmp", "snapshot_02.bmp", "snapshot_03.bmp", "snapshot_04.bmp"]
composePreview = ["preview_01.bmp","preview_02.bmp","preview_03.bmp","preview_04.bmp"]
selMotiv = None   # Nodes des ausgewählten Motivs
selSnap = None    #             und des ausgewählten Schnappschusses
motiv = None      # motiv-Informationen (Klasse Motiv)

# MouseHandler-Routinen
def onMouseOver():
    pnode = pl.getCurEvent().node
    pnode.opacity = 1
    if scr.currScreen=="snapshot_select":  # balken existiert nur auf diesem screen
       balkenX = 196 + ( int(pnode.id[9])-1 )*220
       pl.getElementByID('balken').x = balkenX
       pl.getElementByID('balken').opacity = 1

def onMouseOut():
    pnode = pl.getCurEvent().node
    pnode.opacity = 0.5
    if scr.currScreen=="snapshot_select":
       pl.getElementByID('balken').opacity = 0

def onMouseDown():
    pnode = pl.getCurEvent().node
    pnode.opacity = 0.2

def sendClick():
    reactive_states = ("ScrSav","CoinOp","Preview")
    if control.current_state in reactive_states:
      control.event("click")

def sendReturn():
    reactive_states = ("Preview")
    if control.current_state in reactive_states:
      control.event("return")

def processClick(): # auch in "CamReady" ?
    reactive_states = ("CamReady","TakePics")
    if control.current_state in reactive_states:
        if ourCamera.snapshot_counter==5:
             # CamReady --(readyforSnapshot)--> TakePictures  (starten)
             control.event("click")  
        elif ourCamera.snapshot_counter>0: # 4.,3.,2.,1. Aufruf
             ourCamera.flash_screen.start()  # Nächsten Snapshot anwerfen
             # am Ende des Countdowns wird ourCamera.snapshot() als finished_f aufgerufen

# onMouseUp()-Routine für <div id="motivauswahl">
def selectingMotiv():
# Angeklicktes Postkartenmotiv zuweisen, 
# vorbereiten der Beleuchtung, Camera, rgb-Farbwerte
    global selMotiv, motiv
    selMotiv = pl.getCurEvent().node
    print "Motiv "+selMotiv.href+" gewählt."
    motiv = Motiv(selMotiv)
    # Auswahl der Kontrolle (state machine) mitteilen :
    control.event("selected")

# onMouseUp()-Routine für <div id="snapshot_select">
def selectingSnapshot():
    global selSnap
    selSnapCont = pl.getCurEvent().node
    selSnap = pl.getElementByID('snap'+selSnapCont.id[9])
    print "Schnappschuss "+selSnap.href[-5:-4]+" gewählt."
    selSnap.opacity = 1
    control.event("selected")

# Um Münzeinwurf zu simulieren, muss im AVG-File diese Funktion an onkeypressed gebunden werden
def keyPressed():  # im normalen Betrieb nicht aktiv
    global simulation
    key = pl.getCurEvent().keystring
    if key=="q" or key=="Q":
       pl.showCursor(1)
       usbBoard.lightsOff()       
       progQuit=open("q","w")
       progQuit.write("Manual termination at "+time.asctime())
       progQuit.close()
       pl.getElementByID('camera').stop()
       pl.stop()
       sys.exit()
    if scr.currScreen == "muenzeinwurf":
       simulation=True
       usbBoard.simulateCoinOp(key)


# build up a finite state machine (FSM) as a clear and concise model of
# all possible state transitions
class StateMachine:
    def __init__(self,blob=None):
        self.state_transitions={}
        self.current_state=None
        self.blob=blob
        self.default_transition={}

    def add_state(self,state):
        self.state_transitions[state]={}
        self.default_transition[state]={}

    def add_transition(self, initial_state, event, action, new_state):
        assert(callable(action))
        self.state_transitions[initial_state][event]=(action,new_state)

    def add_default_transition(self, initial_state, action, new_state):
        self.default_transition[initial_state]=(action,new_state)
    def dot_export(self,fname):
        out=open(fname,"w")
        out.write("digraph fsm {concentrate=true\n")
        nodesdict={}
        for i,name in enumerate(self.state_transitions):
            nodesdict[name]=i
            out.write("node%02i [label=\"%s\"]\n"%(i,name))
        for i,name in enumerate(self.state_transitions):
            for event in self.state_transitions[name].keys():
                out.write("node%02i -> node%02i [label=\"%s\" headlabel=\"%s()\"]\n" %(nodesdict[name],nodesdict[self.state_transitions[name][event][1]],event,self.state_transitions[name][event][0].__name__))
        out.write("}\n")
        out.close()

    def event(self,event):
        print "Event (%s) received in state <<%s>>"%(event,self.current_state)
        trans=self.state_transitions[self.current_state]
        try:
            action,new_state=trans[event]
            print "Trying %s()"%action.__name__
        except KeyError:
            try:
                action,new_state=self.default_transition[self.current_state]
                print "default transition %s"%action.__name__
            except KeyError:
                raise KeyError("Event (%s) not found in state <<%s>>"%(event,self.current_state))
        if self.blob is None:
            action()
        else:
            action(self.blob)
        self.current_state=new_state
        print "Entering state : <<%s>>"%new_state

    def start(self,start_state):
        self.current_state=start_state
# end of StateMachine class.

class Motiv:
   def __init__(self, selNode):
      self.rgbVal = {'r':255,'g':255,'b':255}
      motivInfoFile = file(selNode.href[:-6]+"rt.data",'r')  # Infos zum Motiv holen
      # motivInfo_2 = file(...+"pr.data",'r')
      lines = motivInfoFile.readlines()  # (Beleuchtung & zu ersetzender Bildausschnitt)    
      motivInfoFile.close()
      coord = lines[0].split()
      self.ell = {'x':int(coord[0]),'y':int(coord[1]),'a':int(coord[2]),'b':int(coord[3])}
      print "Ell.:("+str(self.ell['x'])+" | "+str(self.ell['y'])+")"
      bytevalues = lines[1].split()
      self.rgbVal['r'] = int(bytevalues[0])     # 0 : schwarzweiß, 1-255 : farbig
      self.rgbVal['g'] = int(bytevalues[1])
      self.rgbVal['b'] = int(bytevalues[2])
      self.lightsOnOff = lines[2]
# end of Motiv class.


class Screen:
  # constant class properties
  displaySteps = 30
  listOfNodes = ("screensaver","motivauswahl","muenzeinwurf",
                 "camera_screen","snapshot_select","photomontage","waitscreen")
  def __init__(self, player):
     self.pl = player
     self.oneFrame = 40 # msec #### recalc !
     self.currScreen = Screen.listOfNodes[0]
     self.lastScreen = self.currScreen
     self.dimState = 0
     self.pic = 0
     self.step = 0
     self.scrSaver = AVGCallback(self.pl, self.fadePictures, 1, name="FadePictures")
     self.waitforCoins = AVGCallback( self.pl, usbBoard.checkCoinInput,
                                    250, name="waitForCoinInput" )
     self.checkCoinsReturn = AVGCallback(self.pl, usbBoard.geldCheck, 1000, name="checkCoinReturn")

     self.motivSel_timeout = CountDown(self.pl, 30, counting_f=None,
                                 finished_f=lambda pl:control.event("time"),
                                 name="MotivSel")
     self.coins_timeout = CountDown(self.pl, 60, counting_f=None,
                                 finished_f=lambda pl:control.event("time"),
                                 name="Coins", display=True )
     self.snapSel_timeout = CountDown (self.pl, 40, counting_f=None, finished_f=lambda pl:control.event("time"), name="SnapSel", display=True)

     self.confPrint_timeout = CountDown (self.pl, 28, counting_f=None, finished_f=lambda pl:control.event("time"), name="ConfPrint", display=True)
     self.scrSaver.start()
     print "Screen : __init__ done"

  def __str__(self):
     return str(self.currScreen)

  # Bildschirm-Umschaltung : neue <div>-node activ
  def gotoScreen(self, newScreen):
     self.lastScreen = self.currScreen
     print 
     print "from : "+self.lastScreen
     assert( newScreen in Screen.listOfNodes )
     self.currScreen = newScreen
     print "to   : "+self.currScreen
     self.pl.getElementByID(self.lastScreen).active = False
     self.pl.getElementByID(self.currScreen).active = True
     print

  def gotoStart(self,):
     print "going back to Start (Screensaver)!"
     self.pl.showCursor(0)
     # Hochgezoomtes Vorschaubild zurückstellen für nächsten Durchlauf
     self.gotoScreen('muenzeinwurf')
     self.pl.getElementByID('selmotiv_container').y = 310
     self.pl.getElementByID('selmotiv').x = 0
     self.pl.getElementByID('selmotiv').y = 0
     self.pl.getElementByID('selmotiv').width  = 700
     self.pl.getElementByID('selmotiv').height = 467
     self.pl.getElementByID('selmotiv').opacity = 1.0      
     self.gotoScreen("screensaver")
     resetGlobals()
     self.scrSaver.start()

  def fadePictures(self):  # sauberer Bilderfader (fuer den ScrSaver-Modus)
     dimState = self.dimState
     pic = self.pic
     fadeDuration = 45.0
     dimState += 1
     if dimState == fadeDuration:
          dimState = 0
          pic=(pic+1)%5
     currImage = self.pl.getElementByID('bild'+str(pic))
     currImage.opacity = 0.2+0.4+0.4*math.sin((dimState/fadeDuration)*2*math.pi+3*math.pi/2)
     #######                                                             = 3.5*math.pi
     self.dimState = dimState
     self.pic = pic

  def prepSelection(self):  # Vorbereitung der Motivauswahl
      global selMotiv, selSnap
      self.scrSaver.stop()
      if self.coins_timeout.running:
        self.coins_timeout.stop()
      self.motivSel_timeout.start()
      selMotiv = None
      selSnap = None
      print "preparing Selection screen",
      self.gotoScreen("motivauswahl")
      self.pl.showCursor(1)
      self.pl.getElementByID('selected_motiv').opacity = 0
      for i in range(numTemplates):
        self.pl.getElementByID('motiv'+str(i+1)).z = 1
        self.pl.getElementByID('motiv'+str(i+1)).opacity = 0.5

  def prepMuenzEinwurf(self): # Vorbereitung des Muenzeinwurfs
     self.motivSel_timeout.stop()
     self.coins_timeout.start()
     self.gotoScreen("muenzeinwurf")
     self.pl.showCursor(0)
     #Großes Vorschaubild zur Positionierung anzeigen
     #(Ellipsenförm. Ausschnitt, dahinter Kamerabild zu sehen)
     self.pl.getElementByID('selmotiv_container').y = 310
     self.pl.getElementByID('selmotiv').href = selMotiv.href[:-6]+"gr.png" #
     self.pl.getElementByID('muenz').opacity = 1
     self.pl.getElementByID('coin').opacity = 1
     self.pl.getElementByID('kein_wechsel').opacity = 1
     self.pl.getElementByID('no_change').opacity = 1
     self.pl.getElementByID('anderes').opacity = 1
     self.pl.getElementByID('other').opacity = 1
     # polling Velleman-IO-Board --> Münzeinwurf ?
     self.waitforCoins.start()

  def zoomMotiv(self):
      global zoom
      steps = Screen.displaySteps
      factor = 2.5  # Hochzoomen bis auf diesen Faktor
      to_x = motiv.ell['x']-2.000*motiv.ell['a']
      to_y = motiv.ell['y']-1.333*motiv.ell['b']
      # von 700x466 nach 2100x1400 : factor = 1.0 --> 2.5
      x_step = factor*to_x/steps
      y_step = factor*to_y/steps
      if self.pl.getElementByID('selmotiv_container').y > 0:
         self.pl.getElementByID('selmotiv_container').y -= 306/steps
         self.pl.getElementByID('selmotiv').width  += (700*(factor-1.0))/steps
         self.pl.getElementByID('selmotiv').height += (466*(factor-1.0))/steps
         self.pl.getElementByID('selmotiv').x -= x_step
         self.pl.getElementByID('selmotiv').y -= y_step
         print "prev.x,.y = ( %i, %i )"%(self.pl.getElementByID('selmotiv').x, self.pl.getElementByID('selmotiv').y)
         self.pl.getElementByID('selmotiv').opacity -= 0.7/steps
      else:
         print "Picture zoomed to (%i,%i)."%(to_x,to_y)
         zoom.stop()
         self.step = 0
         control.event("actionDone")
      self.step += 1

  def prepCamera(self):
      usbBoard.setLights(motiv.lightsOnOff)
      self.checkCoinsReturn.start()
      self.gotoScreen('camera_screen')
      # MotivXxyyzz_po.png : Positionierungsbild (Ausgeschnittene Kopfellipse) 
      self.pl.getElementByID('preview_maske').href = selMotiv.href[:-6]+"po.png"
      self.pl.getElementByID('preview_maske').opacity = 1
      self.pl.getElementByID('rand_maske').opacity = 1
      self.pl.getElementByID('posi').opacity = 1
      self.pl.getElementByID('posi_en').opacity = 1
      self.pl.getElementByID('aufnahmen').opacity = 0
      self.pl.getElementByID('photos_to_take').opacity = 0
      self.pl.getElementByID('aufnahmen_counter').text=str(numSnapshots)
      self.pl.getElementByID('aufnahmen_counter').opacity= 0
      ourCamera.liveMode()    # Kamera an !

  def prepSnapPreview(self):  # Alle Snapshots im Kasten: Bildervorschau aufbauen
      global selSnap, motiv, composePreview
      # Hochgezoomtes Vorschaubild zurückstellen für nächsten Durchlauf
      self.pl.getElementByID('selmotiv_container').y = 310
      self.pl.getElementByID('selmotiv').x = 0
      self.pl.getElementByID('selmotiv').y = 0
      self.pl.getElementByID('selmotiv').width  = 700
      self.pl.getElementByID('selmotiv').height = 467
      self.pl.getElementByID('selmotiv').opacity = 1.0
      # Nächster Bildschirm
      #self.gotoScreen("snapshot_select")
      selSnap = None
      # Vorschaubilder erzeugen, Ausschnittvergößerung darstellen
      for i in range(numSnapshots):
         self.pl.getElementByID('snap_cont'+str(i+1)).active = True
         currSnap = self.pl.getElementByID('snap'+str(i+1))
         composePreview = photoPath+"preview_0"+str(i+1)+".bmp"
         # Vorschaubilder 1,2,3,4 erzeugen, in insertFace wird 'compose' aufgerufen
         insertFace( photoPath+"snapshot_0"+str(i+1)+"_flp.bmp",
                      selMotiv.href[:-6]+"rt.png", composePreview )
         currSnap.href = composePreview
      self.previewAllSnapshots()

  def previewAllSnapshots(self): # Und Bildervorschau (evtl. erneut) anzeigen
                                 # wird von obiger Funktion aufgerufen oder direkt
      global selSnap, motiv
      self.confPrint_timeout.stop()
      self.snapSel_timeout.stop()
      self.snapSel_timeout.start()
      print "Ellipse ( %i,%i | %i,%i )"%(motiv.ell['x'],motiv.ell['y'],motiv.ell['a'],motiv.ell['b'])
      selSnap = None
      self.pl.showCursor(1)
      if self.currScreen!="snapshot_select":
         self.gotoScreen("snapshot_select")
      for i in range(numSnapshots):
         self.pl.getElementByID('snap_cont'+str(i+1)).active = True
         currSnap = self.pl.getElementByID('snap'+str(i+1))
         currSnap.x = -(motiv.ell['x']-motiv.ell['a']-36)
         currSnap.y = -(motiv.ell['y']-motiv.ell['b']-80)
         currSnap.opacity = 1

  def showSelPreview(self):
      global selSnap
      if selSnap == None:  # choose 1 by default, if none was selected
        selSnap = pl.getElementByID('snap1')
      self.snapSel_timeout.stop() # Alten Countdown stoppen (falls grad zurueck v. preview-screen)
      #self.confPrint_timeout.stop()   #########  noetig ?? ##########
      self.confPrint_timeout.start() # und neuen starten
      self.pl.showCursor(0)
      self.gotoScreen("photomontage")  # die Vorschau anzeigen (komplettes Bild)
      self.pl.getElementByID('warten2').opacity=0
      self.pl.getElementByID('wait2').opacity=0
      self.pl.getElementByID('bestaetigung').opacity=1
      self.pl.getElementByID('confirm').opacity=1
      self.pl.getElementByID('rueck').opacity=1
      self.pl.getElementByID('return_to_prev').opacity=1
      self.pl.getElementByID('result').href = selSnap.href
      self.pl.getElementByID('result').opacity = 1

  def prepWaitscreen(self):
      self.pl.showCursor(0)
      self.confPrint_timeout.stop()
      self.pl.getElementByID('warten2').opacity=1
      self.pl.getElementByID('wait2').opacity=1
      self.pl.getElementByID('bestaetigung').opacity=0
      self.pl.getElementByID('confirm').opacity=0
      self.pl.getElementByID('rueck').opacity=0
      self.pl.getElementByID('return_to_prev').opacity=0
      self.pl.setTimeout(500,printPostcard)
# end of Screen class.


# Camera-Klasse für Methoden der Kamera, Livebild und Snapshots machen/abspeichern
class Camera:
   from itertools import cycle
   opacVals = (0.0, 1.0, 1.0, 0.0, 0.0)
   opacity_iter = cycle(opacVals)

   def __init__(self, player, minfps):
      self.pl = player
      self.camNode = self.pl.getElementByID('camera')
      self.camNode.play()
      def opacityChanger(pl,counter):
         self.pl.getElementByID("whitescreen").opacity = Camera.opacity_iter.next()

      self.inactivity_timeout=CountDown(self.pl, 90, counting_f=None,
                                        finished_f=self.sendTime, name="DoSnapshots", display=True)
      # inactivity_timeout 75 sec initially, ends with sendTime() (-->beginFlash())
      self.nextpic_timeout=CountDown(self.pl, 8, counting_f=None,
                                     finished_f=self.beginFlash, name="next Pic")
      # next Pic terminates by calling beginFlash()
      self.flash_screen=CountDown(self.pl, len(Camera.opacVals),
                                  counting_f=opacityChanger, finished_f=self.takeSnapshot,
                                  timestep=40, name="flash")
      # flash terminates by calling takeSnapshot()
      self.later_init()
      print "Camera : __init__ done"

   def later_init(self): # to be called after camera.play()
      print "later_init of Camera"
      self.camNode.whitebalance=14379
      self.camNode.saturation=110
      # make camera act as a "mirror" : flip picture horizontally
      for y in range(self.camNode.getNumVerticesY()):
         for x in range(self.camNode.getNumVerticesX()):
             pos = self.camNode.getOrigVertexCoord(x,y)
             pos.x = 1-pos.x   # flip +x to -x, leave pos.y untouched
             self.camNode.setWarpedVertexCoord(x,y,pos)

   def liveMode(self):  # Here we go!
      self.snapshot_counter=numSnapshots+1
      self.camNode.opacity=1
      self.inactivity_timeout.start()

   # camera acquired, first 'onmousedown' : calls this function
   def readyforSnapshot(self):
      usbBoard.cashIn()
      if self.inactivity_timeout.running:
        self.inactivity_timeout.stop()
      self.nextpic_timeout.start() # endet mit beginFlash
      # Evtl eingeblendetes Timeout-Overlay ausblenden
      self.pl.getElementByID('posi').opacity = 0
      self.pl.getElementByID('posi_en').opacity = 0
      # Warte-Hinweis vom vorigen Durchlauf muss ausgeblendet sein
      self.pl.getElementByID('warten1').opacity = 0
      self.pl.getElementByID('wait1').opacity = 0
      self.pl.getElementByID('aufnahmen').opacity = 1
      self.pl.getElementByID('photos_to_take').opacity = 1
      self.pl.getElementByID('aufnahmen_counter').opacity = 1
      self.snapshot_counter -= 1   # 'numSnapshots' Aufnahmen sind zu machen

   def sendTime(self,pl):
      control.event("time")

   # called when timeout for next picture expires (5 sec)
   def beginFlash(self,pl):
      self.flash_screen.start()  # ends by saving snapshot

   # called via 'onmouseup' from camera_acquire screen, or after countdown expiry
   def takeSnapshot(self,pl):
      if self.snapshot_counter>0: # more snaps to be shot
        pl.getElementByID('aufnahmen_counter').text = str(self.snapshot_counter-1)
        if self.snapshot_counter==1:
          pl.getElementByID('aufnahmen_counter').opacity=0
        self.saveSnapshot()
        self.snapshot_counter-=1
        print "Snapshot counter from %i to %i" % (self.snapshot_counter+1,self.snapshot_counter)
        self.nextpic_timeout.stop()

      if self.snapshot_counter>0: # more snaps ? nextpic : end procedure
        self.nextpic_timeout.start()
      else:       # == 0 : end procedure
        self.nextpic_timeout.stop()
        self.inactivity_timeout.stop()
        pl.getElementByID('aufnahmen_counter').opacity = 0
        pl.getElementByID('aufnahmen').opacity = 0
        pl.getElementByID('photos_to_take').opacity = 0
        pl.getElementByID('warten1').opacity = 1
        pl.getElementByID('wait1').opacity = 1
        if scr.waitforCoins.interval_id:
          scr.waitforCoins.stop() # eigtl schon vorher gestoppt worden, sonst wären wir nicht hier
        ##### Notwendigkeit überprüfen ! ######
        if scr.checkCoinsReturn.interval_id:
          scr.checkCoinsReturn.stop()  # Jetzt gibts kein Zurück mehr !
        self.cleanup()

   # snapshot-Saver, called from above routine
   def saveSnapshot(self):
      photoFile = photoPath+"snapshot_0"+str(5-self.snapshot_counter)+".bmp"
      print "Saving "+photoFile
      try:
         self.camNode.getBitmap().save(photoFile)
         os.system("cp "+photoPath+photoFile+" "+photoPath+photoFile[:-4]+"_flp.bmp")
         os.system("mogrify -flop "+photoPath+photoFile[:-4]+"_flp.bmp")  # "flop" = flip horizontally
      except:
         print "Sorry !! Saving screenshot impossible!"
      if usbBoard.coinsInserted:
        if not usbBoard.coinsTaken:
           usbBoard.cashIn()  # now coins are Taken  # Münzen eingenommen

   def hide(self):
      self.camNode.opacity=0

   def cleanup(self):
      self.hide()
      usbBoard.lightsOff()
      control.event("actionDone")  # All snapshots saved, now call scr.prepSnapPreview()
      print "cleanup after snapshots - actionDone has been sent."
# end of Camera class


# Velleman class for k8055 USB-Board by Velleman
# takes control of coin input
class Velleman:
   def __init__(self,player,dev=0):
       # KONSTANTEN
       self.Card = avg.Velleman(player,0)
       self.device = dev
       self.cashBit = 6
       self.rejectBit = 7
       # VARIABLEN
       self.portAct = 0
       self.coinsInserted = False # Münzsumme (Preis1) eingeworfen
       self.coinsTaken = False     # Münzzwischenkasse geleert, Geld angenommen
       self.coinsRejected = False    #        --  "  --         , Geld ausgeworfen
       self.blink = False
       self.lightsOff()
       print "Velleman USB I/O : init() done"

   def simulateCoinOp(self, key):
       if key=='1':
          self.portAct = 4  # Einwurf <---------------- CHECK ----------#############
       elif key=='2':
          self.portAct = 4  # Einwurf
       elif key=='0':
          self.portAct = 5  # Rückgabe <-------------- CHECK -------------#############
       else:
          self.portAct=0
       print "Setting port active "+str(self.portAct) 

   def checkCoinInput(self):
       global zoom, photoPath
       #if os.path.exists(photoPath+"amount_paid"):
       if self.Card.getInput(4):
          self.portAct = 4
       if self.Card.getInput(5):
          self.portAct = 5   # this overrides '4'          
       if self.portAct>0:
          print "Velleman : Signal"
          scr.waitforCoins.stop()
          scr.coins_timeout.stop()
       if self.portAct==5:    # Clear-signal: 00010000
          responsive_states = ("CoinOp","CamReady","TakePics")
          if control.current_state in responsive_states:
             control.event("coinsRet")
             if os.path.exists(photoPath+"amount_paid"):
                os.remove(photoPath+"amount_paid")
             if self.coinsInserted:
                self.reject()
       elif self.portAct==4:  # Münzsummensignal: 00001000
          if not self.coinsTaken:
             self.coinsInserted=True  # Damit wird "taking coins" moeglich (kassieren)
          if control.current_state == "CoinOp":
             control.event("coinsIn")
             persist = file(photoPath+"amount_paid","w")
             persist.write("Münzen eingeworfen : "+time.asctime())
             persist.close()
          pl.getElementByID('muenz').opacity = 0
          pl.getElementByID('kein_wechsel').opacity = 0
          pl.getElementByID('coin').opacity = 0
          pl.getElementByID('no_change').opacity = 0
          pl.getElementByID('anderes').opacity = 0
          pl.getElementByID('other').opacity = 0
          statistik_update()
          zoom = AVGCallback(pl, scr.zoomMotiv, 1, name="MotivZoom")
          zoom.start()   # sendet am Ende an control das event "actionDone" ! 

   def geldCheck(self):  # checke Signal "Geld in MZK / Bereit zu kassieren oder auswurf"
       global simulation
       if self.coinsTaken:
          scr.checkCoinsReturn.stop()
          return  #  Rueckgabe nicht mehr moeglich
       # Rueckgabe noch moeglich :
       if simulation==True:
          return
       status = self.Card.getInput(4)
       if status==True:
         print "Geld ist da."
       else:
         print "Kein Geld mehr!! OK, zurueck auf Start !"
         scr.checkCoinsReturn.stop()
         if control.current_state in ("CamReady","TakePics"):
           control.event("coinsRet")

   def cashIn(self):  # Geld aus Zwischenkasse annehmen (kassieren, keine Rückgabe mehr mögl)
       self.Card.setOutput(self.cashBit,True)
       self.coinsTaken = True
       self.coinsInserted = False
       pl.setTimeout(1000, lambda:self.Card.setOutput(self.cashBit,False))

   def reject(self):  # Softwarebasierter Abbruch mit Geldrueckgabe, evtl unnoetig
       self.Card.setOutput(self.rejectBit,True)
       control.event("coinsRet") 
       pl.setTimeout(1000, lambda:self.Card.setOutput(self.rejectBit,False))

   def setLights(self, lightSetting):
       for i in range(len(lightSetting)):
         if lightSetting[i]=='0':
           self.Card.setOutput(i,False)
         elif lightSetting[i]=='1':
           self.Card.setOutput(i, True)
         self.lightSetting = lightSetting

   def blinkenLights(self):     # Lampe im Druckausgabefach blinken lassen.
       self.blink = (not self.blink)
       self.Card.setOutput(3, self.blink)  # Lampe an Anschluss 4 (0d1000 gesetzt)

   def lightsOff(self):  # not just lights off, also set cash/reject indicators to 0
       for i in range(8): 
          self.Card.setOutput(i, False)

# end of Velleman class


# Statistik der Motiv-aufrufe
# Es werden nur die mitgezählt, die auch tatsächlich bezahlt wurden
def statistik_update():
    global selMotiv
    stat_file = open("../media/Statistik.log",'a') # append to selected motives list
    line = "\n"+time.asctime()+"  "+selMotiv.href[:-7] # timestamp + motiv name
    stat_file.write(line)
    stat_file.close()

# Bildmontagefunktion
def insertFace(face, motivBgrd, composition):   # alle Param. Dateinamen mit Pfaden
    global selMotiv,photoPath
    bgrdDescription = motivBgrd[:-4]+".data" # Beschreibung des Motivs (Durchstanzbereich für Snapshot)
    faceDescription = photoPath+"snapshot.data"
    # externer Algorithmus 'compose' von Christian Hartmann schneidet Kopf
    # vorm Greenscreen (-g) aus und fügt ihn passgenau u. skaliert ins Zielmotiv ein
    cmdString = "./compose -1g -f20 -v -r108 "
    cmdString += motivBgrd+" "+bgrdDescription+" "+face+" "+faceDescription+" "+composition
    # composition : Zieldatei (Preview 01..04 oder postcard_final)
    print
    print "Doing "+cmdString
    os.system(cmdString)

def printPostcard():
    global lpCheck, switchOnOff, photoPath
    postcardFile = photoPath+"postcard_final.bmp"
    if os.path.exists(postcardFile):  # gedruckte Bilder sichern (Kontrolle, Persistenz)
      os.system("/home/boxadmin/photobox/scripts/archive_png "+postcardFile+" &")

    # try:
    insertFace(photoPath+"snapshot"+selSnap.href[-7:-4]+"_flp.bmp", selMotiv.href[:-6]+"pr.png", postcardFile)
    # except(ImageMagickBlobError):
    #   control.event("alert")
    #   return
    scr.gotoScreen('waitscreen')
    pl.getElementByID('huepfender_fussball').play()
    print selMotiv.href[:-6]+"pr.png"
    startBlinken = pl.setTimeout(15500, blinken)
    endBlinken  =  pl.setTimeout(25000, lambda:control.event("time"))
    #lpCheck = AVGCallback(pl,checkPrinter,2000,name="PrintFinishedChecker")
    #lpCheck.start()
    # in Berlin : lpString = "lp -o position=center -o ppi=287 "+str(postcardFile)
    # in Bremen:
    lpString = "lp -o media=A5 -o landscape -o position=center -o ppi=287 "+str(postcardFile)
    os.system(lpString)
    os.remove(photoPath+"amount_paid")

####################
def checkPrinter():
    global lpCheck, blinken
    # Wiederholt in die lpq gucken,ob Druckjob noch verarbeitet wird, d.h."postcard" darin vorhanden ist
    print "Moment - noch nicht soweit!"
    if os.system("/usr/bin/lpq | /usr/bin/grep -v postcard")==0:
       print "nun ist die Queue leer !"
       lpCheck.stop()
       timedBlinker = CountDown(pl, 30, counting_f=usbBoard.blinkenLights, finished_f=lambda:cosntrol.event("time"), timestep=500)
       timedBlinker.start()
####################

# Lampe über Druckerausgabefach blinken lassen
def blinken():
    global switchOnOff, lampsOnOff
    switchOnOff = AVGCallback(pl,usbBoard.blinkenLights,500,name="blinken")
    switchOnOff.start()

def resetGlobals():
    global lampsOnOff, simulation, selMotiv, selSnap, zoom, snap, pic, dimState
    lampsOnOff = [False, False, False]
    usbBoard.lightsOff()  # Aufruf resetGlobals und restart ueberpruefen !
    usbBoard.portAct = 0
    usbBoard.coinsInserted = False
    usbBoard.coinsTaken = False   
    usbBoard.coinsRejected = False
    usbBoard.blink = False
    ourCamera.inactivity_timeout.stop()
    simulation=False
    selMotiv = None
    selSnap = None
    zoom = None
    snap = 0
    pic = 0
    dimState = 0

def restart():  # nach dem Signal "time", zur Vorbereitung des Übergangs nach "ScrSav"
    global switchOnOff, lampsOnOff
    if switchOnOff:
      switchOnOff.stop()
    print "Starting all over..."
    resetGlobals()
    usbBoard.lightsOff()
    pl.showCursor(0)
    # Hochgezoomtes Vorschaubild zurückstellen für nächsten Durchlauf
    scr.gotoScreen('muenzeinwurf')
    pl.getElementByID('selmotiv_container').y = 310
    pl.getElementByID('selmotiv').x = 0
    pl.getElementByID('selmotiv').y = 0
    pl.getElementByID('selmotiv').width  = 700
    pl.getElementByID('selmotiv').height = 467
    pl.getElementByID('selmotiv').opacity = 1.0      
    scr.gotoScreen('screensaver')
    for i in range(5):   # Bild0..4 zurücksetzen
        pl.getElementByID('bild'+str(i)).opacity=0.2
        pl.getElementByID('bild'+str(i)).z = 1
    scr.scrSaver.start()

###########  "main" (top-level) startet hier  ###########

pl.setDisplayEngine(avg.OGL)
pl.setResolution(1,1280,1024,24)
pl.showCursor(0)
pl.loadFile(avgFile)

# Persistenz des Münzeinwurfs
if os.path.exists(photoPath+"amount_paid"):
  os.remove(photoPath+"amount_paid")
usbBoard = Velleman(pl,0)  # USB-Relais-Steuerkarte, device 0
ourCamera = Camera(pl,15)  # 15 fps
scr = Screen(pl)

control = StateMachine()
states=('ScrSav','MotivSel','CoinOp','ZoomingUp','CamReady',
        'TakePics','SnapSel','Preview','WaitForPrint')
for st in states:
   control.add_state(st)

control.add_transition("ScrSav","click", action=scr.prepSelection, new_state="MotivSel")
control.add_transition("MotivSel","time", action=scr.gotoStart, new_state="ScrSav")
control.add_transition("MotivSel","selected",action=scr.prepMuenzEinwurf,new_state="CoinOp")
control.add_transition("CoinOp","click", action=scr.prepSelection, new_state="MotivSel")
control.add_transition("CoinOp","time", action=scr.gotoStart, new_state="ScrSav")
control.add_transition("CoinOp","coinsIn", action=scr.zoomMotiv, new_state="ZoomingUp")
control.add_transition("CoinOp","coinsRet", action=scr.gotoStart, new_state="ScrSav")
control.add_transition("ZoomingUp","actionDone",action=scr.prepCamera ,new_state="CamReady")
control.add_transition("CamReady","time", action=ourCamera.readyforSnapshot, new_state="TakePics")
control.add_transition("CamReady","click", action=ourCamera.readyforSnapshot, new_state="TakePics")
control.add_transition("CamReady","coinsRet", action=scr.gotoStart, new_state="ScrSav")
control.add_transition("TakePics","coinsRet", action=scr.gotoStart, new_state="ScrSav")
control.add_transition("TakePics","actionDone",action=scr.prepSnapPreview,new_state="SnapSel")
control.add_transition("SnapSel","selected",action=scr.showSelPreview, new_state="Preview")
control.add_transition("SnapSel","time",action=scr.showSelPreview, new_state="Preview")
control.add_transition("Preview","return",action=scr.previewAllSnapshots, new_state="SnapSel")
#control.add_transition("Preview","coinsRet", action=restart, new_state="ScrSav")
control.add_transition("Preview","click", action=scr.prepWaitscreen, new_state="WaitForPrint")
control.add_transition("Preview", "time", action=scr.prepWaitscreen, new_state="WaitForPrint")
control.add_transition("WaitForPrint", "time", action=restart, new_state="ScrSav")

control.add_default_transition("ScrSav", action=scr.prepSelection, new_state="MotivSel")
control.add_default_transition("MotivSel", action=scr.prepMuenzEinwurf, new_state="CoinOp")
control.add_default_transition("SnapSel", action=scr.prepSnapPreview, new_state="SnapSel")
control.add_default_transition("WaitForPrint", action=restart, new_state="ScrSav")
control.dot_export("/tmp/photobox.dot")
control.start("ScrSav")

pl.setFramerate(30)
pl.play()
# Abbruch mit 'Esc' möglich, Cleanup aller Grafik- und Device-Resourcen erfolgt automatisch

print
print "Programm gestoppt."
##################   eoc.  #######################
