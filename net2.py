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
        print "connection made"
        if self.isServer:
            self.parent.addConnection(self)
            self.delegate.handle_ClientConnected(self)
        else:
            self.delegate.handle_ConnectedToServer()            
    
    def dataReceived(self, data):
        self.recvBuffer += data
        log.debug("recvBuffer size: %d" % len(self.recvBuffer))
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
        print "serving"
        self.connections = []
        endpoint = TCP4ServerEndpoint(reactor, port)
        delegate.setDispatcher(self)
        endpoint.listen(SyncFactory(delegate, self))
    
    def dispatch(self, d, exclude=None):
        for conn in self.connections:
            if conn is not exclude:
                conn.dispatch(d)
    
    def addConnection(self, conn):
        self.connections.append(conn)

class SyncClient(object):
    def __init__(self, server, port, delegate):
        delegate.setDispatcher(self)
        self.delegate = delegate
        print "connecting to server"
        point = TCP4ClientEndpoint(reactor, server, port)
        self.protocol = SyncProtocol(False, delegate)
        d = connectProtocol(point, self.protocol)
        print "waiting for callback"
        d.addCallback(self._gotProtocol)

    def _gotProtocol(p):
        print "connection established"
        self.protocol = p
        self.delegate.handle_ConnectedToServer()
    
    def dispatch(self, d, exclude=None):
        self.protocol.dispatch(d)

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
