# Copyright 2017 MDSLAB - University of Messina
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
import os
import pkg_resources
import signal
from stevedore import extension
import sys


# Iotronic imports
from iotronic_lightningrod.Board import Board
import iotronic_lightningrod.wampmessage as WM


# Global variables
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
SESSION = None
global board
board = None
reconnection = False
RPC = {}


@inlineCallbacks
def moduleReloadInfo(session, details):
    """This function is used in the reconnection phase to register again the RPCs of each module.

    :param session:
    :param details:
    :return:
    """

    try:

        yield session.call(str(board.agent) + '.stack4things.connection', uuid=board.uuid, session=details.session)

        for mod in RPC:
            LOG.debug("- Module reloaded: " + str(mod))
            """
            for meth in RPC[mod]:
                LOG.debug("   - RPC reloaded: " + str(meth[0]))
            """
            moduleWampRegister(session, RPC[mod])

    except Exception as e:
        LOG.warning("Board connection call error: {0}".format(e))
        ByeLogo()
        os._exit(1)


def moduleWampRegister(session, meth_list):
    """This function register for each module methods the relative RPC.

    :param session:
    :param meth_list:
    :return:
    """

    for meth in meth_list:
        # We don't considere the __init__ and finalize methods
        if (meth[0] != "__init__") & (meth[0] != "finalize"):

            # LOG.debug(" --> " + str(meth[1]))
            rpc_addr = u'iotronic.' + board.uuid + '.' + meth[0]
            # LOG.debug(" --> " + str(rpc_addr))
            session.register(inlineCallbacks(meth[1]), rpc_addr)
            LOG.info("    --> " + str(meth[0]))

    LOG.info("   Procedures registered!")


def modulesLoader(session):
    """Modules loader method thorugh stevedore libraries

    :param session:
    :return:
    """

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

        LOG.info('Modules to load:')

        for ext in modules.extensions:

            # print(ext.name)

            if (ext.name == 'gpio') & (board.type == 'server'):
                print('- GPIO module disabled for laptop devices')

            else:
                mod = ext.plugin(board, session)

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


@inlineCallbacks
def onBoardConnected(board, session, details):
    """Function called to connect the board to Iotronic (after the first registration process).

    The board:
     1. logs in to Iotronic
     2. loads the modules
    :param board:
    :param session:
    :param details:
    :return:

    """

    global SESSION
    SESSION = session

    try:

        res = yield session.call(str(board.agent) + '.stack4things.connection',
                                 uuid=board.uuid, session=details.session)

        w_msg = WM.deserialize(res)

        if w_msg.result == WM.SUCCESS:
            LOG.info("Access granted to Iotronic: " + str(w_msg.message))

            # LOADING BOARD MODULES
            try:

                yield modulesLoader(session)

            except Exception as e:
                LOG.warning("WARNING - Could not register procedures: {0}".format(e))
                ByeLogo()
                os._exit(1)

        else:
            LOG.error("Access denied to Iotronic: " + str(w_msg.message))
            ByeLogo()
            os._exit(1)

    except Exception as e:
        LOG.warning("Board connection call error: {0}".format(e))
        ByeLogo()
        os._exit(1)


class WampFrontend(ApplicationSession):
    """Function to manage the WAMP connection events.

    """

    @inlineCallbacks
    def onJoin(self, details):

        global SESSION
        SESSION = self

        board.session = self
        board.session_id = details.session
        # LOG.debug(" - session: " + str(details))

        if reconnection is False:

            LOG.info(" - Joined in WAMP-Agent:")
            LOG.info("   - wamp agent: " + str(board.agent))
            LOG.info("   - session ID: " + str(details.session))

            LOG.info("Lightning-rod initialization starting...")

            if board.uuid is None:

                # FIRST BOARD REGISTRAION:
                # If in the LR configuration file there is not the Board UUID specified it means
                # the board is a new one and it has to call Iotronic in order to complete the registration

                try:

                    LOG.info(" - Board needs to be registered to Iotronic.")

                    res = yield self.call(u'stack4things.register', code=board.code, session=details.session)

                    w_msg = WM.deserialize(res)

                    # LOG.info(" - Board registration result: \n" + json.loads(w_msg.message, indent=4))

                    if w_msg.result == WM.SUCCESS:

                        LOG.info("Registration authorized by Iotronic: " + str(w_msg.message))

                        # the message field contains the board configuration to load
                        board.setConf(w_msg.message)

                        # We need to disconnect the client from the registration-agent in
                        # order to reconnect to the WAMP agent assigned by Iotronic at the provisioning stage
                        LOG.info("\n\nDisconnecting from Registration Agent to load new settings...\n\n")
                        self.disconnect()

                    else:
                        LOG.error("Registration denied by Iotronic: " + str(w_msg.message))
                        ByeLogo()
                        os._exit(1)

                except Exception as e:
                    LOG.warning(" - Board registration call error: {0}".format(e))
                    ByeLogo()
                    os._exit(1)

            else:

                # AFTER FIRST BOARD REGISTRAION
                if board.status == "registered":

                    # In this case we manage the first reconnection after the provisioning phase:
                    # at this stage LR sets its status to "operative"
                    LOG.info("\n\n\nBoard is becoming operative...\n\n\n")
                    board.updateStatus("operative")
                    board.loadSettings()

                # After the WAMP connection stage LR will contact its WAMP agent and load the enabled modules
                onBoardConnected(board, self, details)

        else:
            # If the board is in connection recovery state we need to register again the RPCs of each module
            yield moduleReloadInfo(self, details)
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
        if (reconnection is False) & (board.status != "registered"):
            # NORMAL STATE: we need to recover wamp session
            reconnection = True

            LOG.debug("Reconnecting to " + str(connector.getDestination()))
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        else:
            # REGISTRATION STATE
            LOG.debug("\n\nReconnecting after registration...\n\n")

            # LR load the new configuration and gets the new WAMP-Agent
            board.loadSettings()

            # LR has to connect to the assigned WAMP-Agent
            wampConnect(board.wamp_config)


def wampConnect(wamp_conf):

    component_config = types.ComponentConfig(realm=unicode(wamp_conf['realm']))
    session_factory = wamp.ApplicationSessionFactory(config=component_config)
    session_factory.session = WampFrontend

    transport_factory = WampClientFactory(session_factory, url=wamp_conf['url'])
    transport_factory.autoPingInterval = 1
    transport_factory.autoPingTimeout = 1

    connector = websocket.connectWS(transport_factory)

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

        global board
        board = Board()

        LOG.info('Info:')
        LOG.info(' - Logs: /var/log/s4t-lightning-rod.log')
        current_time = board.getTimestamp()
        LOG.info(" - Current time: " + current_time)

        self.w = WampManager(board.wamp_config)

        self.w.start()

    def stop_handler(self, signum, frame):
        LOG.info("LR is shutting down...")

        self.w.stop()

        ByeLogo()

        os._exit(1)
