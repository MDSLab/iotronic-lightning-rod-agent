#!/usr/bin/env python

# Autobahn and Twisted imports
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor, defer
from autobahn.twisted import wamp, websocket
from autobahn.twisted.util import sleep
from autobahn.wamp import types



# OSLO imports
from oslo_config import cfg
from oslo_log import log as logging

# MODULES imports
from stevedore import extension, named
import pkg_resources
import inspect
import threading
from config import entry_points_name



# LR configuration

# Logging configuration
LOG = logging.getLogger(__name__)

wamp_opts = [
    cfg.StrOpt('wamp_ip',
               default='192.168.17.1',
               help=('URL of wamp broker')),
    cfg.IntOpt('wamp_port',
               default=8181,
               help='port wamp broker'),
    cfg.StrOpt('wamp_transport_url',
            default='ws://192.168.17.1:8181/',
            help=('URL of wamp broker')),
    cfg.StrOpt('wamp_realm',
               default='s4t',
               help=('realm broker')),
]
  
  
CONF = cfg.CONF
CONF.register_opts(wamp_opts, 'wamp')
#print CONF.__dict__


def modulesLoader(session):
    '''
    Modules loader method thorugh stevedore libraries.
    '''
    LOG.debug("Entry-points: " + entry_points_name)
    LOG.info("Available modules: ")
    
    ep=[] 

    for ep in pkg_resources.iter_entry_points(group='s4t.modules'):
	LOG.info(" - "+str(ep))


    if not ep:
      
	LOG.info("No modules available!")
	sys.exit()

    else:

	modules = extension.ExtensionManager(
		namespace='s4t.modules',
		#invoke_on_load=True,
		#invoke_args=(session,),
	)
		
	for ext in modules.extensions:
	  
	  mod = ext.plugin(session)
	  #print mod.name
	  
	  meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)
	  
	  LOG.info("RPC list of "+str(mod.name)+ ":")
	  
	  for meth in meth_list[1:]:		#We don't considere the __init__ method
	     LOG.info( " - " + str(meth) )
	     session.register(inlineCallbacks(meth[1]), u'board.'+meth[0])
	     
	""" 
	t = threading.Thread(target=listener_q, args=(session,))
	t.start()
	"""
            


	  

  

class WampFrontend(ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
      
        LOG.info("WAMP server session ready!")
        
        
        # BOARD REGISTRAION
        try: 
	    res = yield self.call(u'register_board') 
	    LOG.info("Board registration call result: {}".format(res)) 
	except Exception as e: 
	    LOG.warning("Board registration call error: {0}".format(e))
	
	
	try:
	  
            yield modulesLoader(self) #self.register(pinco, u'com.myapp.hello')
            LOG.info("Procedures registered!")
            

        except Exception as e:
            LOG.warning("WARNING - Could not register procedures: {0}".format(e))
	
       
       
    def onLeave(self, details):
        LOG.info('session left: {}'.format(details))

       
       
       
class WampClientFactory(websocket.WampWebSocketClientFactory, ReconnectingClientFactory):
    maxDelay = 30

    def clientConnectionFailed(self, connector, reason):
        #print "reason:", reason
        LOG.warning("Wamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        #print "reason:", reason
        LOG.warning("Wamp Connection Lost.")
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        
        
class WampManager(object):
  
    def __init__(self):
      component_config = types.ComponentConfig(realm = unicode(CONF.wamp.wamp_realm))
      session_factory = wamp.ApplicationSessionFactory(config = component_config)
      session_factory.session = WampFrontend

      """
      transport_factory = WampClientFactory(session_factory)
      transport_factory.host = CONF.wamp.wamp_ip
      transport_factory.port = CONF.wamp.wamp_port
      LOG.debug("WAMP connection parameters:\n\tWamp IP: %s\n\tWamp Port: %s\n\tWamp realm: %s\n", CONF.wamp.wamp_ip, CONF.wamp.wamp_port, CONF.wamp.wamp_realm)
      """
      transport_factory = WampClientFactory(session_factory, url=CONF.wamp.wamp_transport_url)
      transport_factory.autoPingInterval = 1
      transport_factory.autoPingTimeout = 1

      LOG.debug("wamp url: %s wamp realm: %s", CONF.wamp.wamp_transport_url, CONF.wamp.wamp_realm)
      
      websocket.connectWS(transport_factory)

    def start(self):
        LOG.info("Starting WAMP server...")
        reactor.run()
	ByeLogo()

    def stop(self):
        LOG.info("Stopping WAMP-agent server...")
        reactor.stop()
        LOG.info("WAMP server stopped.")



def ByeLogo():
    print "\nBye!"
    LOG.info("Bye!")  


def LogoLR():
    LOG.info('');
    LOG.info('##############################')
    LOG.info('  Stack4Things Lightning-rod')
    LOG.info('##############################')
    
    print ''
    print '##############################'
    print '  Stack4Things Lightning-rod'
    print '##############################'
    print ' - See logs in /var/log/s4t-lightning-rod.log'



class LightningRod(object):
  
    def __init__(self):

      logging.register_options(CONF)
      DOMAIN = "s4t-lightning-rod"
      CONF(project='iotronic')
      logging.setup(CONF, DOMAIN)

      LogoLR()
    
      w=WampManager()

      try:
	  w.start()
      except KeyboardInterrupt:
	  w.stop()
	  exit()
				
    
    
    
