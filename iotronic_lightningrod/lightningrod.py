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
import json
import os
import pkg_resources
import signal
from stevedore import extension
import sys


# Iotronic imports
from config import entry_points_name
from iotronic_lightningrod.Node import Node


# Global variables
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
SESSION = None
global node
node = None
reconnection = False
RPC = {}

"""
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
"""
"""
# Device options
device_group = cfg.OptGroup(name='device', title='Device options')
device_opts = [

    cfg.StrOpt('type',
               default='server',
               help='Device type.'),
]

CONF.register_group(device_group)
CONF.register_opts(device_opts, 'device')
"""


def moduleReloadInfo(session):

    for mod in RPC:
        LOG.debug("- Module reloaded: " + str(mod))
        """
        for meth in RPC[mod]:
            LOG.debug("   - RPC reloaded: " + str(meth[0]))
        """
        moduleWampRegister(session, RPC[mod])


def moduleWampRegister(session, meth_list):

    for meth in meth_list:
        # We don't considere the __init__ and finalize methods
        if (meth[0] != "__init__") & (meth[0] != "finalize"):

            # LOG.debug(" --> " + str(meth[1]))
            rpc_addr = u'iotronic.' + node.uuid + '.' + meth[0]
            # LOG.debug(" --> " + str(rpc_addr))
            session.register(inlineCallbacks(meth[1]), rpc_addr)
            LOG.info("    --> " + str(meth[0]))

    LOG.info("   Procedures registered!")


def modulesLoader(session):
    '''Modules loader method thorugh stevedore libraries.

    '''

    LOG.debug("Entry-points:\n" + entry_points_name)
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

        LOG.info('\n')

        LOG.info('Modules to load:')

        for ext in modules.extensions:

            # print(ext.name)

            if (ext.name == 'gpio') & (node.type == 'server'):
                print('- GPIO module disabled for laptop devices')

            else:
                mod = ext.plugin(node, session)

                # Methods list for each module
                global meth_list
                meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)

                global RPC
                RPC[mod.name] = meth_list

                if len(meth_list) == 2:  # there is only the "__init__" method of the python module

                    LOG.debug(" - No RPC to register for " + str(ext.name) + " module!")

                else:
                    LOG.debug(" - RPC list of " + str(mod.name) + ":")
                    moduleWampRegister(SESSION, meth_list)

                # Call the finalize procedure for each module
                mod.finalize()

        LOG.info("Lightning-rod modules loaded.")
        LOG.info("\n\nListening...")


class WampFrontend(ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):

        global SESSION
        SESSION = self

        node.session = self
        node.session_id = details.session

        # print(" - session: " + str(details))

        # if (reconnection is False) | (node.status == "registered"):
        if reconnection is False:
            LOG.info(" - Joined in WAMP-Agent:")
            LOG.info("   - wamp agent: " + str(node.agent))
            LOG.info("   - session ID: " + str(details.session))

            LOG.info("Lightning-rod initialization starting...")

            if node.uuid is None:

                # FIRST NODE REGISTRAION:
                # If in the LR configuration file there is not the Node UUID specified it means
                # the node is a new one and it has to call Iotronic in order to complete the
                # registration

                try:

                    LOG.info(" - Node needs to be registered to Iotronic.")
                    res = yield self.call(u'stack4things.register',
                                          code=node.code, session=details.session)
                    LOG.info(" - Board registration result: \n" + json.dumps(res, indent=4))

                    node.setConf(res)

                    # We need to disconnect the client from the registration-agent in
                    # order to reconnect to the WAMP agent assigned by Iotronic
                    # at the provisioning stage
                    LOG.info("\n\nDisconnecting from Registration Agent to load new settings...\n\n")
                    self.disconnect()

                except Exception as e:
                    LOG.warning(" - Board registration call error: {0}".format(e))
                    ByeLogo()
                    os._exit(1)

            else:

                # AFTER FIRST NODE REGISTRAION

                if node.status == "registered":
                    # In this case we manage the first reconnection after the provisioning phase:
                    # at this stage LR sets its status to "operative"
                    LOG.info("\n\n\nNode is becoming operative...\n\n\n")

                    node.updateStatus("operative")

                    node.loadSettings()

                # After the WAMP connection stage LR will contact its WAMP agent
                # and load the enabled modules
                try:

                    res = yield self.call(str(node.agent) + '.stack4things.register_uuid',
                                          uuid=node.uuid, session=details.session)

                    # LOADING NODE MODULES
                    try:

                        yield modulesLoader(self)

                    except Exception as e:
                        LOG.warning("WARNING - Could not register procedures: {0}".format(e))
                        ByeLogo()
                        os._exit(1)

                except Exception as e:
                    LOG.warning("Board connection call error: {0}".format(e))
                    ByeLogo()
                    os._exit(1)

        else:
            yield moduleReloadInfo(self)
            LOG.warning("WAMP session recovered!")
            LOG.info("\nListening...")

    @inlineCallbacks
    def onLeave(self, details):
        LOG.info('WAMP session left: {}'.format(details))


class WampClientFactory(websocket.WampWebSocketClientFactory, ReconnectingClientFactory):

    def clientConnectionFailed(self, connector, reason):
        LOG.warning("Wamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        LOG.warning("Wamp Connection Lost.")

        global reconnection
        if (reconnection is False) & (node.status != "registered"):
            # NORMAL STATE
            reconnection = True

            LOG.debug("Reconnecting to " + str(connector.getDestination()))
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        else:
            # REGISTRATION STATE

            LOG.debug("\n\nReconnecting after registration...\n\n")

            # LR load the new configuration and gets the new WAMP-Agent
            node.loadSettings()

            # LR has to connect to the assigned WAMP-Agent
            wampConnect(node.wamp_config)


def wampConnect(wamp_conf):

    component_config = types.ComponentConfig(realm=unicode(wamp_conf['realm']))
    session_factory = wamp.ApplicationSessionFactory(config=component_config)
    session_factory.session = WampFrontend

    transport_factory = WampClientFactory(session_factory, url=wamp_conf['url'])
    transport_factory.autoPingInterval = 1
    transport_factory.autoPingTimeout = 1

    connector = websocket.connectWS(transport_factory)
    # print connector

    LOG.info("WAMP status:")
    LOG.info(" - establishing connection to " + str(connector.getDestination()))


class WampManager(object):
    def __init__(self, wamp_conf):

        wampConnect(wamp_conf)

    def start(self):
        LOG.info(" - starting WAMP server...")
        reactor.run()

        # PROVVISORIO --------------------------------------------------------------
        from subprocess import call
        LOG.debug("Unmounting...")

        try:
            mountPoint = "/opt/BBB"
            # errorCode = self.libc.umount(mountPoint, None)
            errorCode = call(["umount", "-l", mountPoint])

            LOG.debug("Unmount " + mountPoint + " result: " + str(errorCode))

        except Exception as msg:
            result = "Unmounting error:", msg
            LOG.debug(result)
        # --------------------------------------------------------------------------

    def stop(self):
        LOG.info("Stopping WAMP-agent server...")
        reactor.stop()
        LOG.info("WAMP server stopped!")


def ByeLogo():
    LOG.info("Bye!")


def LogoLR():
    LOG.info('')
    LOG.info('##############################')
    LOG.info('  Stack4Things Lightning-rod')
    LOG.info('##############################')


class LightningRod(object):

    def __init__(self):

        logging.register_options(CONF)
        DOMAIN = "s4t-lightning-rod"
        CONF(project='iotronic')
        logging.setup(CONF, DOMAIN)

        signal.signal(signal.SIGINT, self.stop_handler)

        LogoLR()

        global node
        node = Node()

        LOG.info('Info:')
        LOG.info(' - Logs: /var/log/s4t-lightning-rod.log')
        current_time = node.getTimestamp()
        LOG.info(" - Current time: " + current_time)

        self.w = WampManager(node.wamp_config)

        self.w.start()

    def stop_handler(self, signum, frame):
        LOG.info("LR is shutting down...")

        self.w.stop()

        ByeLogo()

        os._exit(1)
