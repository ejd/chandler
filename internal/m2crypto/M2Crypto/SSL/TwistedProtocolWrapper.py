from twisted.protocols.policies import ProtocolWrapper
from twisted.internet import defer
from M2Crypto import BIO, m2
from M2Crypto.SSL import Context, Connection

class TLSProtocolWrapper(ProtocolWrapper):
    """
    A SSL/TLS protocol wrapper to be used with Twisted.

    Usage:
        factory = MyFactory()
        factory.startTLS = True # Starts SSL immediately, otherwise waits
                                # for STARTTLS from peer
        wrappingFactory = WrappingFactory(factory)
        wrappingFactory.protocol = TLSProtocolWrapper
        reactor.connectTCP(host, port, wrappingFactory)

    MyFactory should have the following interface:

        startTLS:                boolean   Set to True to start SSL immediately
        getContext():            function  Should return M2Crypto.SSL.Context()
        sslPostConnectionCheck() function  Should do SSL post connection check

    """
    def __init__(self, factory, wrappedProtocol):
        print 'MyProtocolWrapper.__init__'
        ProtocolWrapper.__init__(self, factory, wrappedProtocol)

        # wrappedProtocol == client/server instance
        # factory.wrappedFactory == client/server factory

        self.data = ''
        self.encrypted = ''

        if hasattr(factory.wrappedFactory, 'getContext'):
            self.ctx = factory.wrappedFactory.getContext()
        else:
            self.ctx = Context()

        if hasattr(factory.wrappedFactory, 'sslPostConnectionCheck'):
            self.sslPostConnectionCheck = factory.wrappedFactory.sslPostConnectionCheck

        self.tlsStarted = False

        if hasattr(factory.wrappedFactory, 'startTLS'):
            if factory.wrappedFactory.startTLS:
                self._startTLS()

    def _startTLS(self):
        self.internalBio = m2.bio_new(m2.bio_s_bio())
        m2.bio_set_write_buf_size(self.internalBio, 8192*8) # XXX change size
        self.networkBio = m2.bio_new(m2.bio_s_bio())
        m2.bio_set_write_buf_size(self.networkBio, 8192*8) # XXX change size
        m2.bio_make_bio_pair(self.internalBio, self.networkBio)

        self.sslBio = m2.bio_new(m2.bio_f_ssl())

        self.ssl = m2.ssl_new(self.ctx.ctx)
        
        m2.ssl_set_connect_state(self.ssl) # XXX client only
        m2.ssl_set_bio(self.ssl, self.internalBio, self.internalBio)
        m2.bio_set_ssl(self.sslBio, self.ssl, 1)

        self.tlsStarted = True

    def makeConnection(self, transport):
        print 'MyProtocolWrapper.makeConnection'
        ProtocolWrapper.makeConnection(self, transport)

    def _encrypt(self, data=''):
        self.data += data
        g = m2.bio_ctrl_get_write_guarantee(self.sslBio)
        if g > 0:
            r = m2.bio_write(self.sslBio, self.data)
            if r < 0:
                assert(m2.bio_should_retry(self.sslBio))
            else:
                self.data = self.data[r:]
        pending = m2.bio_ctrl_pending(self.networkBio)
        if pending > 0:
            encryptedData = m2.bio_read(self.networkBio, pending)
        else:
            encryptedData = ''
        return encryptedData

    def _decrypt(self, data=''):
        self.encrypted += data
        g = m2.bio_ctrl_get_write_guarantee(self.networkBio)
        if g > 0:
            r = m2.bio_write(self.networkBio, self.encrypted)
            if r < 0:
                assert(m2.bio_should_retry(self.networkBio))
            else:
                self.encrypted = self.encrypted[r:]
        pending = m2.bio_ctrl_pending(self.sslBio)
        if pending > 0:
            decryptedData = m2.bio_read(self.sslBio, pending)
        else:
            decryptedData = ''
        return decryptedData

    def write(self, data):
        print 'MyProtocolWrapper.write'
        if not self.tlsStarted:
            ProtocolWrapper.write(self, data)
            return
        
        encryptedData = self._encrypt(data)
        ProtocolWrapper.write(self, encryptedData)

    def writeSequence(self, data):
        print 'MyProtocolWrapper.writeSequence'
        if not self.tlsStarted:
            ProtocolWrapper.writeSequence(self, ''.join(data))
            return

        self.write(''.join(data))

    def loseConnection(self):
        print 'MyProtocolWrapper.loseConnection'
        if self.sslBio:
            m2.bio_free_all(self.sslBio)
            self.sslBio = None
        self.internalBio = None
        self.networkBio = None
        ProtocolWrapper.loseConnection(self)

    def registerProducer(self, producer, streaming):
        print 'MyProtocolWrapper.registerProducer'
        ProtocolWrapper.registerProducer(self, producer, streaming)

    def unregisterProducer(self):
        print 'MyProtocolWrapper.unregisterProducer'
        ProtocolWrapper.unregisterProducer(self)

    def stopConsuming(self):
        print 'MyProtocolWrapper.stopConsuming'
        ProtocolWrapper.stopConsuming(self)

    def connectionMade(self):
        print 'MyProtocolWrapper.connectionMade'
        ProtocolWrapper.connectionMade(self)

    def dataReceived(self, data):
        print 'MyProtocolWrapper.dataReceived'
        if not self.tlsStarted:
            ProtocolWrapper.dataReceived(self, data)
            return

        decryptedData = self._decrypt(data)
        if decryptedData is None:
            decryptedData = ''

        if self.data or m2.bio_ctrl_pending(self.networkBio) > 0:
            encryptedData = self._encrypt()
            ProtocolWrapper.write(self, encryptedData)

        ProtocolWrapper.dataReceived(self, decryptedData)

    def connectionLost(self, reason):
        print 'MyProtocolWrapper.connectionLost'
        print 'data', self.data
        print 'encrypted', self.encrypted        
        ProtocolWrapper.connectionLost(self, reason)

