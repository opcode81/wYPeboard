# (C) 2014 by Dominik Jain (djain@gmx.net)

import asyncore
import socket
import logging
import threading
import pickle
import hashlib

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class Dispatcher(asyncore.dispatcher_with_send):
    def __init__(self, ipv6=False, sock=None):
        asyncore.dispatcher_with_send.__init__(self, sock=sock)
        self.ipv6 = ipv6
        self.terminator = "\r\n\r\n$end$\r\n\r\n"
        self.recvBuffer = ""

    def send(self, data):
        log.debug("sending packet; size %d" % len(data))
        log.debug("hash: %s", hashlib.sha224(data).hexdigest())
        if len(data) > 20000:
            with file("bigdata.dat", "wb") as f:
                f.write(data)
                f.close()
        #asyncore.dispatcher_with_send.send(self, data + self.terminator)
        self.enqueue(data + self.terminator)
    
    def createSocket(self):
        self.create_socket(socket.AF_INET6 if self.ipv6 else socket.AF_INET, socket.SOCK_STREAM)

    def handle_read(self):
        d = self.recv(8192)
        if d == "": # connection closed from other end
            return
        self.recvBuffer += d
        log.debug("recvBuffer size: %d" % len(self.recvBuffer))
        while True:
            try:
                tpos = self.recvBuffer.index(self.terminator)
            except:
                break
            packet = self.recvBuffer[:tpos]
            log.debug("received packet; size %d" % len(packet))
            log.debug("hash: %s", hashlib.sha224(packet).hexdigest())
            if len(packet) > 20000:
                with file("bigdata.dat", "wb") as f:
                    f.write(packet)
                    f.close()
            self.handle_packet(packet)
            self.recvBuffer = self.recvBuffer[tpos+len(self.terminator):]

    def handle_packet(self, packet):
        ''' handles a read packet '''
        log.warning('unhandled packet; size %d' % len(packet))

    def enqueue(self, data):
        self.out_buffer = self.out_buffer + data
        

class SyncServer(Dispatcher):
    def __init__(self, port, delegate, ipv6=False):
        Dispatcher.__init__(self, ipv6=ipv6)
        self.delegate = delegate 
        self.delegate.setDispatcher(self)
        # start listening for connections
        self.createSocket()
        host = ""
        self.bind((host, port))
        self.connections = []
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            return
        log.info("incoming connection from %s" % str(pair[1]))
        conn = DispatcherConnection(pair[0], self)
        self.connections.append(conn)
        # send initial data to new user
        self.delegate.handle_ClientConnected(conn)

    def dispatch(self, d, exclude=None):
        numClients = len(self.connections) if exclude is None else len(self.connections)-1
        if type(d) == dict and "evt" in d:
            evt = d["evt"]
            if evt != "moveUserCursor":
                log.debug("dispatching %s to %d clients" % (evt, numClients))
        for c in self.connections:
            if c != exclude:
                c.dispatch(d)

    def removeConnection(self, conn):
        if not conn in self.connections:
            log.error("tried to remove non-present connection")
        self.connections.remove(conn)
        self.delegate.handle_ClientConnectionLost(conn)
        if len(self.connections) == 0:
            self.delegate.handle_AllClientConnectionsLost()

class DispatcherConnection(Dispatcher):
    def __init__(self, connection, server):
        Dispatcher.__init__(self, sock=connection)
        self.syncserver = server

    def handle_packet(self, packet):
        log.debug("handling packet; size %d" % len(packet))
        if packet == "": # connection closed from other end
            return
        self.syncserver.delegate.handle_PacketReceived(packet, self)

    def remove(self):
        log.info("client connection dropped")
        self.syncserver.removeConnection(self)

    def handle_close(self):
        self.remove()
        self.close()

    def dispatch(self, d):
        self.send(pickle.dumps(d))

class SyncClient(Dispatcher):
    def __init__(self, server, port, delegate, ipv6=False):
        Dispatcher.__init__(self, ipv6=ipv6)
        self.delegate = delegate
        self.delegate.setDispatcher(self)
        self.serverAddress = (server, port)
        self.connectedToServer = self.connectingToServer = False
        self.connectToServer()        

    def connectToServer(self):
        log.info("connecting to %s..." % str(self.serverAddress))
        self.connectingToServer = True
        self.createSocket()
        self.connect(self.serverAddress)

    def handle_connect(self):
        log.info("connected to %s" % str(self.serverAddress))
        self.connectingToServer = False
        self.connectedToServer = True
        self.delegate.handle_ConnectedToServer()

    def handle_packet(self, packet):
        if packet == "": # server connection lost
            return
        self.delegate.handle_PacketReceived(packet, None)

    def handle_close(self):
        self.close()

    def close(self):
        log.info("connection closed")
        self.connectedToServer = False
        asyncore.dispatcher.close(self)
        self.delegate.handle_ConnectionToServerLost()
    
    # connection interface

    def dispatch(self, d, exclude=None):
        if not self.connectedToServer:
            return
        if not (type(d) == dict and "ping" in d):
            pass
        self.send(pickle.dumps(d))
    
    def reconnect(self):
        self.connectToServer()
        

def spawnNetworkThread():
    networkThread = threading.Thread(target=lambda:asyncore.loop(timeout=0.1))
    networkThread.daemon = True
    networkThread.start()

def startServer(port, delegate, wxApp, ipv6=False):
    log.info("serving on port %d, IPv6: %s" % (port, ipv6))
    server = SyncServer(port, delegate, ipv6=ipv6)
    spawnNetworkThread()
    delegate.handle_ServerLaunched()
    wxApp.MainLoop()

def startClient(server, port, delegate, wxApp, ipv6=False):
    log.info("connecting to %s:%d, IPv6: %s" % (server, port, ipv6))
    client = SyncClient(server, port, delegate, ipv6=ipv6)
    spawnNetworkThread()
    wxApp.MainLoop()