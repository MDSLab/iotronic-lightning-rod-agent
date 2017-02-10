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
from stevedore import extension
import sys


# Iotronic imports
from config import entry_points_name
from iotronic_lightningrod.Node import Node


# Global variables
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
SESSION = None
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
        if (meth[0] != "__init__"):  # We don't considere the __init__ method
            LOG.info(" - " + str(meth[0]))
            # LOG.debug(" --> " + str(meth[1]))
            rpc_addr = u'iotronic.' + node.uuid + '.' + meth[0]
            # LOG.debug(" --> " + str(rpc_addr))
            session.register(inlineCallbacks(meth[1]), rpc_addr)

    LOG.info("Procedures registered.")
    LOG.info("Modules loaded.")


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

        LOG.info('Module list:')
        print('Module list:')
        for ext in modules.extensions:

            # print(ext.name)

            if (ext.name == 'gpio') & (node.type == 'server'):
                print('- GPIO module disabled for laptop devices')

            else:
                mod = ext.plugin(node)

                # Methods list for each module
                global meth_list
                meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)

                global RPC
                RPC[mod.name] = meth_list

                if len(meth_list) == 1:  # there is only the "__init__" method of the python module

                    LOG.info(" - No RPC to register for " + str(ext.name) + " module!")

                else:

                    LOG.debug("- RPC list of " + str(mod.name) + ":")

                    moduleWampRegister(SESSION, meth_list)

        print("\nListening...")


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
            LOG.info("Joined in WAMP server:")
            print("WAMP:")
            print (" - session ID: " + str(details.session))
            LOG.debug(" - session ID: " + str(details.session))
            print (json.dumps(node.wamp_config, indent=4))

            LOG.info("Lightning-rod initialization starting...")

            if node.uuid is None:

                # FIRST NODE REGISTRAION:
                # If in the LR configuration file there is not the Node UUID specified it means
                # the node is a new one and it has to call Iotronic in order to complete the
                # registration

                try:

                    LOG.debug("Node needs to be registered to Iotronic...")
                    res = yield self.call(u'stack4things.register',
                                          token=node.token, session=details.session)
                    LOG.info("Board registration call result: {}".format(res))

                    node.setConf(res)

                    # We need to disconnect the client from the registration-agent in
                    # order to reconnect to the WAMP agent assigned by Iotronic
                    # at the provisioning stage
                    self.disconnect()

                except Exception as e:
                    LOG.warning("Board registration call error: {0}".format(e))
                    ByeLogo()
                    os._exit(1)

            else:

                # AFTER FIRST NODE REGISTRAION

                if node.status == "registered":
                    # In this case we manage the first reconnection after the provisioning phase:
                    # at this stage LR relaods the new configuration provided by Iotronic and
                    # set its status to "operative"
                    LOG.info("\n\n\nNode is becoming operative...\n\n\n")
                    node.loadSettings()
                    node.updateStatus("operative")

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
                    print("Board connection call error: {0}".format(e))
                    ByeLogo()
                    os._exit(1)

        else:
            yield moduleReloadInfo(self)
            LOG.warning("WAMP session recovered!")
            print("\nListening...")

    @inlineCallbacks
    def onLeave(self, details):
        LOG.info('WAMP session left: {}'.format(details))
        print("\nWAMP session left.")


class WampClientFactory(websocket.WampWebSocketClientFactory, ReconnectingClientFactory):

    def clientConnectionFailed(self, connector, reason):
        LOG.warning("Wamp Connection Failed.")
        print("\nWamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        LOG.warning("Wamp Connection Lost.")
        print("Wamp Connection Lost.")

        global reconnection
        if (reconnection is False) & (node.status != "registered"):
            reconnection = True
            # print("- reconnection set to " + str(reconnection))
        else:
            LOG.debug("Please wait for node configuration.")

        LOG.debug("Reconnecting...")
        print("Reconnecting...\n")

        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


class WampManager(object):
    def __init__(self, wamp_conf):

        component_config = types.ComponentConfig(realm=unicode(wamp_conf['realm']))
        session_factory = wamp.ApplicationSessionFactory(config=component_config)
        session_factory.session = WampFrontend

        transport_factory = WampClientFactory(session_factory, url=wamp_conf['url'])
        transport_factory.autoPingInterval = 1
        transport_factory.autoPingTimeout = 1

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


class LightningRod(object):

    def __init__(self):

        logging.register_options(CONF)
        DOMAIN = "s4t-lightning-rod"
        CONF(project='iotronic')
        logging.setup(CONF, DOMAIN)

        LogoLR()

        global node
        node = Node()

        print ('Info:')
        print (' - Logs: /var/log/s4t-lightning-rod.log')
        current_time = node.getTimestamp()
        LOG.info("Current time: " + current_time)
        print (" - Current time: " + current_time)

        w = WampManager(node.wamp_config)

        try:
            w.start()
        except KeyboardInterrupt:
            w.stop()
            exit()
