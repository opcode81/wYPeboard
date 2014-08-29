import wx
from twisted.internet import wxreactor
wxreactor.install()

from sys import argv
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from sys import stdout
import logging
import threading
import pickle

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class SyncProtocol(Protocol):
    def __init__(self, isServer, delegate, parent=None):
        self.recvBuffer = ""
        self.terminator = "\r\n\r\n$end$\r\n\r\n"
        self.isServer = isServer
        self.delegate = delegate
        self.parent = parent
    
    def connectionMade(self):
        log.info("connection made: %s", self.transport)
        if self.isServer:
            self.parent.addConnection(self)            
        else:
            self.parent.setConnected(True)
            
    def connectionLost(self, reason=None):
        log.info("connection lost; reason: %s", reason)
        if self.isServer:
            self.parent.removeConnection(self)
        else:
            self.parent.setConnected(False)
            
    def dataReceived(self, data):
        self.recvBuffer += data
        #log.debug("recvBuffer size: %d" % len(self.recvBuffer))
        while True:
            try:
                tpos = self.recvBuffer.index(self.terminator)
            except:
                break
            packet = self.recvBuffer[:tpos]
            log.debug("received packet; size %d" % len(packet))
            self.delegate.handle_PacketReceived(packet, self)
            self.recvBuffer = self.recvBuffer[tpos+len(self.terminator):]
    
    def sendPacket(self, packet):
        self.transport.write(packet + self.terminator)
        
    # connection interface
    
    def dispatch(self, d):
        self.sendPacket(pickle.dumps(d))
    
class SyncFactory(Factory):
    def __init__(self, delegate, server):
        self.delegate = delegate
        self.server = server
    
    def buildProtocol(self, addr):
        return SyncProtocol(True, self.delegate, parent=self.server)

class SyncServer(object):
    def __init__(self, port, delegate):
        log.info("serving on port %d", port)
        self.connections = []
        self.delegate = delegate
        endpoint = TCP4ServerEndpoint(reactor, port)
        delegate.setDispatcher(self)
        endpoint.listen(SyncFactory(delegate, self))

    def addConnection(self, conn):
        self.connections.append(conn)
        self.delegate.handle_ClientConnected(self)
    
    def removeConnection(self, conn):
        self.delegate.handle_ClientConnectionLost(self)
        self.connections.remove(conn)
        if len(self.connections) == 0:
            self.delegate.handle_AllClientConnectionsLost()

    # server interface
    
    def dispatch(self, d, exclude=None):
        for conn in self.connections:
            if conn is not exclude:
                conn.dispatch(d)
    
class SyncClient(object):
    def __init__(self, server, port, delegate):
        delegate.setDispatcher(self)
        self.delegate = delegate
        self.server = server
        self.port = port
        self.connected = False
        self.connect()
    
    def connect(self):
        log.info("connecting to %s:%s", self.server, self.port)
        point = TCP4ClientEndpoint(reactor, self.server, self.port)
        self.protocol = SyncProtocol(False, self.delegate, self)
        d = connectProtocol(point, self.protocol)
    
    def setConnected(self, connected):
        self.connected = connected
        if self.connected:
            self.delegate.handle_ConnectedToServer()
        else:
            self.delegate.handle_ConnectionToServerLost()

    # client interface

    def dispatch(self, d, exclude=None):
        if self.connected:
            self.protocol.dispatch(d)
    
    def reconnect(self):
        self.connect()

def startServer(port, delegate, wxApp):
    SyncServer(port, delegate)
    delegate.handle_ServerLaunched()
    reactor.registerWxApp(wxApp)    
    reactor.run()

def startClient(server, port, delegate, wxApp):
    SyncClient(server, port, delegate)
    reactor.registerWxApp(wxApp)
    reactor.run()

if __name__=='__main__':
    if argv[1] == "serve":
        startServer(8080)
    else:
        startClient("localhost", 8080)
    #reactor.run()
