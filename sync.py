# (C) 2014 by Dominik Jain (djain@gmx.net)

import sys
import pickle
import wx
import time as t
import traceback
from whiteboard import Whiteboard
import objects
import numpy
import time
import logging
from net import *

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class DispatchingWhiteboard(Whiteboard):
	def __init__(self, title, isServer, **kwargs):
		self.isServer = isServer
		self.lastPing = t.time()
		self.lastCursorMoveTime = t.time()
		self.userName = "user " + str(t.time())
		self.remoteUserCursorUpdateInterval = 0.1
		Whiteboard.__init__(self, title, **kwargs)
		self.Centre()
		self.connId2UserName = {}
	
	def onObjectCreationCompleted(self, object):
		self.dispatch(evt="addObject", args=(object.serialize(),))

	def onObjectsDeleted(self, *ids):
		self.dispatch(evt="deleteObjects", args=ids)

	def onObjectsMoved(self, offset, *ids):
		self.dispatch(evt="moveObjects", args=[offset] + list(ids))
	
	def onObjectUpdated(self, objectId, operation, args):
		self.dispatch(evt="updateObject", args=(objectId, operation, args))

	def onCursorMoved(self, pos):
		now = t.time()
		if now - self.lastCursorMoveTime > self.remoteUserCursorUpdateInterval:
			#for i in range(1000):
			self.dispatch(evt="moveUserCursor", args=(self.userName, pos,))
			self.lastCursorMoveTime = now

	def moveUserCursor(self, userName, pos):
		sprite = self.viewer.userCursors.get(userName)
		if sprite is None: return
		sprite.animateMovement(pos, self.remoteUserCursorUpdateInterval)
		#sprite.pos = pos

	def _deserialize(self, s):
		if not type(s) == str:
			return s
		return objects.deserialize(s, self.viewer)

	def addObject(self, object):
		super(DispatchingWhiteboard, self).addObject(self._deserialize(object))
	
	def setObjects(self, objects, dispatch=True):
		log.debug("setObjects with %d objects", len(objects))
		objects = map(lambda o: self._deserialize(o), objects)
		super(DispatchingWhiteboard, self).setObjects(objects)
		if dispatch:
			self.dispatchSetObjects(self.dispatcher)
	
	def dispatchSetObjects(self, dispatcher):
		dispatcher.dispatch(dict(evt="setObjects", args=([o.serialize() for o in self.getObjects()], False)))
	
	def updateObject(self, objectId, operation, args):
		obj = self.viewer.objectsById.get(objectId)
		if obj is None: return
		eval("obj.%s(*args)" % operation)

	def dispatch(self, exclude=None, **d):
		self.dispatcher.dispatch(d, exclude=exclude)

	def handleNetworkEvent(self, d):
		exec("self.%s(*d['args'])" % d["evt"])

	def OnTimer(self, evt):
		Player.OnTimer(self, evt)
		# perform periodic ping from client to server
		if not self.isServer:
			if t.time() - self.lastPing > 1:
				self.lastPing = t.time()
				self.dispatch(ping = True)

	# server delegate methods
	
	def handle_ServerLaunched(self):
		self.Show()
	
	def handle_ClientConnected(self, conn):
 		conn.dispatch(dict(evt="addUser", args=(self.userName,)))
 		self.dispatchSetObjects(conn)

	def handle_ClientConnectionLost(self, conn):
		log.info("client connection lost: %s", conn)
		userName = self.connId2UserName.get(id(conn))
		if userName is not None:
			log.info("connection of user '%s' closed", userName)
			self.deleteUser(userName)
		else:
			log.warning("connection closed, unknown user name")
	
	def handle_AllClientConnectionsLost(self):
		self.errorDialog("All client connections have been closed.")
		
	# client delegate methods
	
	def handle_ConnectedToServer(self):
		self.Show()
		self.dispatch(evt="addUser", args=(self.userName,))

	def handle_ConnectionToServerLost(self):
		self.deleteAllUsers()		
		if self.questionDialog("No connection. Reconnect?\nClick 'No' to quit.", "Reconnect?"):
			self.dispatcher.reconnect()
		else:
			self.Close()
	
	# client/server delegate methods
	
	def handle_PacketReceived(self, data, conn):
		d = pickle.loads(data)
		if type(d) == dict and "ping" in d: # ignore pings
			return
		if type(d) == dict and "evt" in d:
			if d["evt"] == "addUser":
				log.info("addUser from %s with name '%s'", conn, d["args"][0])
				self.connId2UserName[id(conn)] = d["args"][0]
			# forward event to other clients
			if self.isServer:
				self.dispatch(exclude=conn, **d)
			# handle in own player
			self.handleNetworkEvent(d)
	
	def setDispatcher(self, dispatcher):
		self.dispatcher = dispatcher
	
if __name__=='__main__':
	app = wx.App(False)

	argv = sys.argv[1:]
	#size = (1800, 950)
	size = (800, 600)
	isServer = None
	server = None
	ipv6 = False
	help = False
	while len(argv) > 0:
		a = argv[0]
		if a == "serve" and len(argv) >= 2:
			port = int(argv[1])
			isServer = True
			argv = argv[2:]
		elif a == "connect" and len(argv) >= 3:
			server = argv[1]
			port = int(argv[2])
			argv = argv[3:]
		elif a == "--ipv6":
			ipv6 = True
			argv = argv[1:]
		else:
			print "invalid argument: %s" % a
			help = True
			break
	if help:
		appName = "sync.py"
		print "\nwYPeboard\n"
		print "usage:"
		print "   server:  %s [options] serve <port>" % appName
		print "   client:  %s [options] connect <server> <port>" % appName
		print "\noptions:"
		print "   --ipv6   use IPv6 instead of IPv4"
		sys.exit(1)
	whiteboard = DispatchingWhiteboard("wYPeboard server" if isServer else "wYPeboard client", isServer, canvasSize=size)
	if isServer:
		startServer(port, whiteboard, ipv6=ipv6)
	else:
		startClient(server, port, whiteboard, ipv6=ipv6)
	whiteboard.startRendering()
	app.MainLoop()
