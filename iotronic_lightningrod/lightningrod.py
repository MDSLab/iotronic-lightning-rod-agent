# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


# Autobahn and Twisted imports
from autobahn.twisted import wamp
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted import websocket
from autobahn.wamp import types
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor

# OSLO imports
from oslo_config import cfg
from oslo_log import log as logging

# MODULES imports
import inspect
import pkg_resources
from stevedore import extension
import sys

# Iotronic imports
from config import entry_points_name


# LR configuration

# Logging configuration
LOG = logging.getLogger(__name__)

CONF = cfg.CONF

# WAMP opts
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

CONF.register_opts(wamp_opts, 'wamp')

# Device opts
device_group = cfg.OptGroup(name='device', title='Device options')
device_opts = [

    cfg.StrOpt('name',
               default='laptop',
               help='Device type.'),
]

CONF.register_group(device_group)
CONF.register_opts(device_opts, 'device')


def modulesLoader(session):
    '''Modules loader method thorugh stevedore libraries.

    '''

    LOG.debug("Entry-points: " + entry_points_name)
    LOG.info("Available modules: ")

    ep = []

    for ep in pkg_resources.iter_entry_points(group='s4t.modules'):
        LOG.info(" - " + str(ep))

    if not ep:

        LOG.info("No modules available!")
        sys.exit()

    else:

        modules = extension.ExtensionManager(
            namespace='s4t.modules',
            # invoke_on_load=True,
            # invoke_args=(session,),
        )

        print('Module list:')
        for ext in modules.extensions:

            # print(ext.name)

            if (ext.name == 'gpio') & (CONF.device.name == 'laptop'):
                print('- GPIO module disabled for laptop devices')

            else:
                mod = ext.plugin(session)

                print('- ' + mod.name)

                # Methods list for each module
                meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)

                LOG.debug("RPC list of " + str(mod.name) + ":")

                for meth in meth_list:

                    # print meth[0]
                    if (meth[0] != "__init__"):  # We don't considere the __init__ method
                        LOG.debug(" - " + str(meth[0]))
                        session.register(inlineCallbacks(
                            meth[1]), u'board.' + meth[0])


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

            # self.register(pinco, u'com.myapp.hello')
            yield modulesLoader(self)
            LOG.info("Procedures registered.")
            LOG.info("Modules loaded.")

        except Exception as e:
            LOG.warning(
                "WARNING - Could not register procedures: {0}".format(e))

    def onLeave(self, details):
        LOG.info('session left: {}'.format(details))


class WampClientFactory(
        websocket.WampWebSocketClientFactory, ReconnectingClientFactory):

    maxDelay = 30

    def clientConnectionFailed(self, connector, reason):
        # print "reason:", reason
        LOG.warning("Wamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        # print "reason:", reason
        LOG.warning("Wamp Connection Lost.")
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


class WampManager(object):

    def __init__(self):
        component_config = types.ComponentConfig(
            realm=unicode(CONF.wamp.wamp_realm))
        session_factory = wamp.ApplicationSessionFactory(
            config=component_config)
        session_factory.session = WampFrontend

        transport_factory = WampClientFactory(
            session_factory, url=CONF.wamp.wamp_transport_url)
        transport_factory.autoPingInterval = 1
        transport_factory.autoPingTimeout = 1

        LOG.debug("wamp url: %s wamp realm: %s",
                  CONF.wamp.wamp_transport_url, CONF.wamp.wamp_realm)

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
    print ("\nBye!")
    LOG.info("Bye!")


def LogoLR():
    LOG.info('')
    LOG.info('##############################')
    LOG.info('  Stack4Things Lightning-rod')
    LOG.info('##############################')

    print ('')
    print ('##############################')
    print ('  Stack4Things Lightning-rod')
    print ('##############################')
    print ('Info:')
    print (' - Logs: /var/log/s4t-lightning-rod.log')


class LightningRod(object):

    def __init__(self):

        logging.register_options(CONF)
        DOMAIN = "s4t-lightning-rod"
        CONF(project='iotronic')
        logging.setup(CONF, DOMAIN)

        LogoLR()

        print("Device: " + CONF.device.name)

        w = WampManager()

        try:
            w.start()
        except KeyboardInterrupt:
            w.stop()
            exit()
