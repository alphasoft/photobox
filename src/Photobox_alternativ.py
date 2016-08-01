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
                       +  V.0.13.0  +
                       +  13-04-06  +
                       +------------+
"""
import sys, os, time
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
mediaPath = "../media/"
photoPath = "../output/" ######  <--------- ÜBERPRÜFEN !!! #######
ourCamera = None    # Objekt der eigenen Klasse Camera (s.u.)

# Globale Variablen, Handles u. Namenslisten für den Programmablauf
simulation = False
coinsIn = 0        # Hat Münzeinwurf stattgefunden ?
flashing = 0       # Während des Blitzens ist dieses Callback aktiv
zoom = 0           # hineinzoomen ins gewählte Motiv auf Kopfbereich
scrSaver = 0
switchOnOff = None
photoFile = ["snapshot_01.png", "snapshot_02.png", "snapshot_03.png", "snapshot_04.png"]
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
    print "Schnappschuss "+selSnap.href[-9:-8]+" gewählt."
    selSnap.opacity = 1
    control.event("selected")

# Um Münzeinwurf zu simulieren, muss im AVG-File diese Funktion an "onkeypressed" gebunden werden
def keyPressed():
    key = pl.getCurEvent().keystring
    if key=="q" or key=="Q":
       pl.showCursor(1)
       os.system("touch q")
       sys.exit()
    if scr.currScreen == "muenzeinwurf":
       #control.event("key")
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
      self.infoFile = file(selNode.href[:-6]+"rt.data",'r')  # Infos zum Motiv holen
      # motivInfo_2 = file(...+"pr.data",'r')
      lines = self.infoFile.readlines()  # (Beleuchtung & zu ersetzender Bildausschnitt)    
      self.infoFile.close()
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
  displaySteps = 25
  opacVals = (0.0, 0.2, 0.2, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.0, 1.0, 1.0,
              1.0, 1.0, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.2, 0.2, 0.2)
  listOfNodes = ("screensaver","motivauswahl","muenzeinwurf",
                   "camera_screen","snapshot_select","photomontage","waitscreen")
  # the instance
  def __init__(self, player):
     self.pl = player
     self.oneFrame = 40 # msec #### recalc !
     self.currScreen = Screen.listOfNodes[0]
     self.lastScreen = self.currScreen
     self.dimState = 0
     self.pic = 0
     self.step = 0
     self.scrSaver = AVGCallback(self.pl, self.flipPictures, 125, name="FlipPictures")
     self.waitforCoins = AVGCallback( self.pl, usbBoard.checkCoinInput,
                                    300, name="waitForCoinInput" )
     self.selection_timeout = CountDown(self.pl, 40, counting_f=None,
                                 finished_f=lambda pl:control.event("time"),
                                 name="SnapSel", display=False)
     self.coins_timeout = CountDown(self.pl, 70, counting_f=None,
                                 finished_f=lambda pl:control.event("time"),
                                 name="CoinsIn", display=True )
     self.scrSaver.start()
     print "Screen : __init__ done"

  def __str__(self):
     return str(self.currScreen)

  def reset(self):
     pass

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
     pl.showCursor(0)
     self.gotoScreen("screensaver")
     resetGlobals()
     self.scrSaver.start()

  def flipPictures(self): # scrSaver: Bilder hervortreten lassen und wieder faden.
      dimState = self.dimState
      pic = self.pic
      # opacity durchsteppen im 0.1 sec Takt
      if dimState==0:
         dimState=1
      self.pl.getElementByID('bild'+str(pic)).opacity = Screen.opacVals[dimState]
      dimState = (dimState + 1) % len(Screen.opacVals)
      if dimState==(len(Screen.opacVals)-1):
         pic = (pic + 1) % 5
      self.dimState = dimState
      self.pic = pic

  def prepSelection(self):  # Vorbereitung der Motivauswahl
      global selMotiv, selSnap
      self.scrSaver.stop()
      if self.coins_timeout.running:
        self.coins_timeout.stop()
      self.selection_timeout.start()
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
     self.selection_timeout.stop()
     self.coins_timeout.start()
     self.pl.showCursor(0)
     self.gotoScreen("muenzeinwurf")
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
      global zoom, motiv
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
      self.pl.getElementByID('selmotiv').height = 466
      self.pl.getElementByID('selmotiv').opacity = 1.0
      # Nächster Bildschirm
      self.gotoScreen("snapshot_select")
      selSnap = None
      # Vorschaubilder erzeugen, Ausschnittvergößerung darstellen
      for i in range(numSnapshots):
         currSnap = self.pl.getElementByID('snap'+str(i+1))
         currSnap.href = photoPath+"snapshot_0"+str(i+1)+"_flp.bmp"
         print "%i: %s" % (i,currSnap.href)
         currSnap.x = -240
         currSnap.y = -100
         currSnap.width=200
         currSnap.height=280
         currSnap.opacity = 1
      self.previewAllSnapshots()

  def previewAllSnapshots(self): # Und Bildervorschau (evtl. erneut) anzeigen. (Wird von obiger Funktion aufgerufen oder direkt)
      global selSnap, motiv
      self.selection_timeout.stop()
      self.selection_timeout.start()
      print "Ellipse ( %i,%i | %i,%i )"%(motiv.ell['x'],motiv.ell['y'],motiv.ell['a'],motiv.ell['b'])
      selSnap = None
      if self.currScreen!="snapshot_select":
         self.gotoScreen("snapshot_select")
      self.pl.showCursor(1)

  def showSelPreview(self):
      global selSnap, selMotiv, photoPath
      if selSnap == None:  # choose 1 by default, if none was selected
        selSnap = pl.getElementByID('snap1')
      print selMotiv.href[:-6]+"pr.png"
      self.selection_timeout.stop()
      self.selection_timeout.start()
      # mount postcard preview
      insertFace(selSnap.href,selMotiv.href[:-6]+"pr.png",photoPath+"postcard_final.bmp")
      # show it and ask for input
      self.gotoScreen("photomontage")
      self.pl.getElementByID('warten2').opacity=0
      self.pl.getElementByID('wait2').opacity=0
      self.pl.getElementByID('bestaetigung').opacity=1
      self.pl.getElementByID('confirm').opacity=1
      self.pl.getElementByID('rueck').opacity=1
      self.pl.getElementByID('return_to_prev').opacity=1
      self.pl.getElementByID('result').href = photoPath+"postcard_final.bmp"
      self.pl.getElementByID('result').opacity = 1

  def prepWaitscreen(self):
      self.pl.showCursor(0)
      self.selection_timeout.stop()
      self.pl.getElementByID('warten2').opacity=1
      self.pl.getElementByID('wait2').opacity=1
      self.pl.getElementByID('bestaetigung').opacity=0
      self.pl.getElementByID('confirm').opacity=0
      self.pl.getElementByID('rueck').opacity=0
      self.pl.getElementByID('return_to_prev').opacity=0
      self.pl.setTimeout(100,printPostcard)
# end of Screen class.


# Camera-Klasse für Methoden der Kamera, Livebild und Snapshots machen/abspeichern
class Camera:
   from itertools import cycle
   opacVals = (0.0, 1.0, 0.0)
   opacity_iter = cycle(opacVals)

   def __init__(self, player, minfps):
      self.pl = player
      self.camNode = self.pl.getElementByID('camera')
      self.camNode.play()
      self.pl.setTimeout(1000,self.later_init)
      def opacityChanger(pl,counter):
         self.pl.getElementByID("whitescreen").opacity = Camera.opacity_iter.next()

      self.inactivity_timeout=CountDown(self.pl, 22, counting_f=None,
                                        finished_f=self.sendTime, name="DoSnapshots", display=True)
      # inactivity_timeout 75 sec initially, ends with sendTime() (-->beginFlash())
      self.nextpic_timeout=CountDown(self.pl, 7, counting_f=None,
                                     finished_f=self.beginFlash, name="nextpic")
      # next Pic terminates by calling beginFlash()
      self.flash_screen=CountDown(self.pl, len(Camera.opacVals),
                                  counting_f=opacityChanger, finished_f=self.takeSnapshot,
                                  timestep=40, name="flash")
      # flash terminates by calling takeSnapshot()
      print "Camera : __init__ done"

   def later_init(self): # to be called directly after player has initialized
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
      self.snapshot_counter -= 1   #  damit es losgehen kann

   def sendTime(self,pl):
      control.event("time")

   # called when timeout for next picture expires (5 sec)
   def beginFlash(self,pl):
      self.flash_screen.start()  # ends by saving snapshot

   # called via 'onmouseup' from camera_acquire screen, or after countdown expiry
   def takeSnapshot(self,pl):
      self.later_init()
      if self.snapshot_counter>0: # more snaps to be shot
        pl.getElementByID('aufnahmen_counter').text = str(self.snapshot_counter-1)
        self.saveSnapshot()
        self.snapshot_counter-=1
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
        scr.waitforCoins.stop()
        self.cleanup()

   # snapshot-Saver, called from above routine
   def saveSnapshot(self):
      photoFile = photoPath+"snapshot_0"+str(5-self.snapshot_counter)+".bmp"
      print "Saving "+photoFile
      try:
         self.camNode.getBitmap().save(photoFile)
         os.system("cp "+photoFile+" "+photoFile[:-4]+"_flp.bmp")
         try:
           os.system("mogrify -flop "+photoFile[:-4]+"_flp.bmp")
         except:
           print "" 
         # "flopped.png" for flipped pictures
      except:
         print "Sorry !! Saving screenshot impossible!"

   def hide(self):
      self.camNode.opacity=0

   def cleanup(self):
      self.hide()
      control.event("actionDone")  # All snapshots saved, now call scr.prepSnapPreview()
      print "cleanup after snapshots - actionDone has been sent."
# end of Camera class


# Velleman class for k8055 USB-Board by Velleman
# takes control of coin input
class Velleman:
   def __init__(self,player,dev=0):
       global simulation
       self.device = dev
       self.portAct = 0
       self.blink = False
       self.pl = player
       # self.Card = avg.Velleman(player,0)  # Hardwae-Instanz
       ## nötig für Eingänge abfragen, Ausgänge setzen
       print "Velleman USB I/O : init() done"
       simulation=True

   def simulateCoinOp(self, key):
       if key=='1':
          self.portAct = 4  # Einwurf
       elif key=='2':
          self.portAct = 4  # Einwurf
       elif key=='0':
          self.portAct = 5  # Rückgabe
       else:
          self.portAct = 0
       print "Setting port active "+str(self.portAct) 

   def checkCoinInput(self):
       global zoom
       if simulation==False:
          if os.path.exists(photoPath+"amount_paid"):
             inputs = [5]
          else:
             inputs = [4, 5]
          for i in inputs:  # 4 und 5 sind abzufragen
             if self.Card.getInput(i):
               self.portAct = i
       elif simulation==True:
          pass

       if self.portAct>0:
          print "Velleman : Signal"
          scr.waitforCoins.stop()
          scr.coins_timeout.stop()
       if self.portAct==5:    # Clear-signal: 00010000
          responsive_states = ("CoinOp","CamReady") # "TakePics"
          if control.current_state in responsive_states:
             control.event("coinsRet")
             if os.path.exists(photoPath+"amount_paid"):
                os.remove(photoPath+"amount_paid")
          # und wieder von vorn (zurück zum Screensaver)
       elif self.portAct==4:  # Münzsummensignal: 00001000
          if control.current_state == "CoinOp":
             control.event("coinsIn")
             persist = file("../output/amount_paid","w")
             persist.write("Münzen eingeworfen : "+time.asctime())
             persist.close()
          pl.getElementByID('muenz').opacity = 0
          pl.getElementByID('kein_wechsel').opacity = 0
          pl.getElementByID('coin').opacity = 0
          pl.getElementByID('no_change').opacity = 0
          pl.getElementByID('anderes').opacity = 0
          pl.getElementByID('other').opacity = 0
          statistik_update()
          zoom = AVGCallback(pl, scr.zoomMotiv, 80, name="MotivZoom")
          zoom.start()

   def setLights(self, lightSetting):
       if simulation:
           return
       for i in range(len(lightSetting)):
         if lightSetting[i]=='0':
           self.Card.setOutput(i,False)
         elif lightSetting[i]=='1':
           self.Card.setOutput(i, True)
         self.lightSetting = lightSetting

   def blinkenLights(self):     # Lampe im Druckausgabefach blinken lassen.
       if simulation:
           return
       self.blink = (not self.blink)
       self.Card.setOutput(3, self.blink)  # Lampe an Anschluss 4 (0d1000 gesetzt)

   def lightsOff(self):
       if simulation:
           return
       for i in range(4):
          self.Card.setOutput(i, False)

   def sendSignal(self, port):
       if simulation:
           return
       self.Card.setOutput(4, True)
       pass
# end of Velleman class


# Statistik der Motiv-aufrufe
# Es werden nur die mitgezählt, die auch tatsächlich bezahlt wurden
def statistik_update():
    global selMotiv
    stat_file = open(mediaPath+"Statistik.log",'a') # append to selected motives list
    line = "\n"+time.asctime()+"  "+selMotiv.href[:-7] # timestamp + motiv name
    stat_file.write(line)
    stat_file.close()

# Bildmontagefunktion
def insertFace(face, motivBgrd, composition):  # alle Param. Dateinamen mit Pfaden
    global selMotiv
    bgrdDescription = selMotiv.href[:-6]+"pr.data" # Beschreibung des Motivs (Durchstanzbereich für Snapshot)
    faceDescription = photoPath+"snapshot.data"
    # externer Algorithmus 'compose' von Christian Hartmann schneidet Kopf
    # vorm Greenscreen (-g) aus und fügt ihn passgenau u. skaliert ins Zielmotiv ein
    cmdString = "./compose -1g -f25 -v "
    cmdString += motivBgrd+" "+bgrdDescription+" "+face+" "+faceDescription+" "+composition
    print
    print "Doing "+cmdString
    os.system(cmdString)

def printPostcard():
    global lpCheck, switchOnOff
    postcardFile = photoPath+"postcard_final.bmp"
    #  Postkarte erzeugen
    scr.gotoScreen('waitscreen')
    pl.getElementByID('drucken').opacity = 1
    pl.getElementByID('printing').opacity = 1
    pl.getElementByID('huepfender_fussball').play()
    print selMotiv.href[:-6]+"pr.png"
    #lpCheck = AVGCallback(pl,checkPrinter,2000,name="PrintFinishedChecker")
    #lpCheck.start()
    #  on finished(Printjob), call blinkenLights
    startBlinken = pl.setTimeout(10500, blinken)    
    endBlinken  =  pl.setTimeout(22000, lambda:control.event("time"))
    lpString = "lp -o landscape -o position=center -o media=A5 -o ppi=300 "+str(postcardFile)
    os.system(lpString)
    os.remove(photoPath+"amount_paid")

#################### wird momentan nicht benutzt !

def checkPrinter():
    global lpCheck, blinken
    # Wiederholt in die lpq gucken,ob Druckjob noch verarbeitet wird, d.h."postcard" darin vorhanden ist
    if os.system("/usr/bin/lpq | /usr/bin/grep -v postcard")==0:
       print "nun ist die Queue leer !"
       lpCheck.stop()
       timedBlinker = CountDown(pl, 30, counting_f=usbBoard.blinkenLights, finished_f=lambda:control.event("time"), timestep=500)
       timedBlinker.start()

####################

# Lampe über Druckerausgabefach blinken lassen
def blinken():
    global switchOnOff, lampsOnOff
    switchOnOff = AVGCallback(pl,usbBoard.blinkenLights,500,name="blinken")
    switchOnOff.start()

def resetGlobals():
    global lampsOnOff, selMotiv, selSnap, snap, zoom, pic, dimState
    usbBoard.portAct = 0
    usbBoard.lightsOff()
    lampsOnOff = [False, False, False]
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
    usbBoard.setLights([ False, False, False ])
    pl.showCursor(0)
    scr.gotoScreen('screensaver')
    for i in range(5):   # Bild0..4 zurücksetzen
        pl.getElementByID('bild'+str(i)).opacity=0.2
        pl.getElementByID('bild'+str(i)).z = 1
    scr.scrSaver.start()

###########  "main" (top-level) starts here  ###########

pl.setDisplayEngine(avg.OGL)
pl.setResolution(0,1280,1024,24)  # (1,1280,1024,24) : eigener Screen
pl.showCursor(0)
pl.loadFile(avgFile)

# mit Programmstart amount_paid entfernen ??
if os.path.exists(photoPath+"amount_paid"):
  os.remove(photoPath+"amount_paid")

usbBoard = Velleman(pl,0)  # USB-Relais-Steuerkarte, device 0
ourCamera = Camera(pl,30)  # 15 fps
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
control.add_transition("Preview","coinsRet", action=restart, new_state="ScrSav")
control.add_transition("Preview","click", action=scr.prepWaitscreen, new_state="WaitForPrint")
control.add_transition("Preview", "time", action=scr.prepWaitscreen, new_state="WaitForPrint")
control.add_transition("WaitForPrint", "time", action=restart, new_state="ScrSav")

control.add_default_transition("ScrSav", action=scr.prepSelection, new_state="MotivSel")
control.add_default_transition("MotivSel", action=scr.prepMuenzEinwurf, new_state="CoinOp")
control.add_default_transition("SnapSel", action=scr.prepSnapPreview, new_state="SnapSel")
control.add_default_transition("WaitForPrint", action=restart, new_state="ScrSav")
control.dot_export("/tmp/photobox.dot")
control.start("ScrSav")

pl.play()
# Abbruch mit 'Esc' möglich, Cleanup aller Grafik- und Device-Resourcen erfolgt automatisch
print
print "Programm gestoppt."
##################   eoc.  #######################