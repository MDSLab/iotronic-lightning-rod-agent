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
from autobahn.wamp import exception
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
import socket
from stevedore import extension
import sys


# Iotronic imports
from iotronic_lightningrod.Board import Board
import iotronic_lightningrod.wampmessage as WM
from iotronic_lightningrod.common.exception import timeoutRPC


# Global variables
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
SESSION = None
global board
board = None
reconnection = False
RPC = {}
RPC_devices = {}


#from iotronic_lightningrod.modules import device_manager

#@inlineCallbacks
def moduleReloadInfo(session, details):
    """This function is used in the reconnection phase to register again the RPCs of each module.

    :param session:
    :param details:
    :return:
    """

    LOG.info("Modules reloading after WAMP recovery...")

    try:

        for mod in RPC:
            LOG.info("- Reloading module RPcs for " + str(mod))
            moduleWampRegister(session, RPC[mod])

        for dev in RPC_devices:
            LOG.info("- Reloading device RPCs for " + str(dev))
            moduleWampRegister(session, RPC_devices[dev])


    except Exception as err:
        LOG.warning("Board modules reloading error: " + str(err))
        Bye()


def moduleWampRegister(session, meth_list):
    """This function register for each module methods the relative RPC.

    :param session:
    :param meth_list:
    :return:
    """

    if len(meth_list) == 2:

        LOG.info("   - No procedures to register!")

    else:

        for meth in meth_list:
            # We don't considere the __init__ and finalize methods
            if (meth[0] != "__init__") & (meth[0] != "finalize"):
                rpc_addr = u'iotronic.' + board.uuid + '.' + meth[0]
                session.register(inlineCallbacks(meth[1]), rpc_addr)
                LOG.info("   --> " + str(meth[0]))
                #LOG.info("    --> " + str(rpc_addr))

        #LOG.info("    Procedures registered!")


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
                LOG.info('- GPIO module disabled for laptop devices')

            else:
                mod = ext.plugin(board, session)

                # Methods list for each module
                global meth_list
                meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)

                global RPC
                RPC[mod.name] = meth_list

                if len(meth_list) == 2:  # there are the"__init__" and "finalize" methods for each module

                    LOG.info(" - No RPC to register for " + str(ext.name) + " module!")

                else:
                    LOG.info(" - RPC list of " + str(mod.name) + ":")
                    moduleWampRegister(SESSION, meth_list)

                # Call the finalize procedure for each module
                mod.finalize()

        LOG.info("Lightning-rod modules loaded.")
        LOG.info("\n\nListening...")


@inlineCallbacks
def IotronicLogin(board, session, details):
    """Function called to connect the board to Iotronic (after the first registration process).

    The board:
     1. logs in to Iotronic
     2. loads the modules
    :param board:
    :param session:
    :param details:
    :return:

    """

    LOG.info("Iotronic Authentication...")

    global reconnection

    global SESSION
    SESSION = session

    try:

        rpc = str(board.agent) + u'.stack4things.connection'

        with timeoutRPC(seconds=3, action=rpc):
            res = yield session.call(rpc, uuid=board.uuid, session=details.session)

        w_msg = WM.deserialize(res)

        if w_msg.result == WM.SUCCESS:

            LOG.info(" - Access granted to Iotronic.") #: " + str(w_msg.message))

            # LOADING BOARD MODULES
            try:

                yield modulesLoader(session)

            except Exception as e:
                LOG.warning("WARNING - Could not register procedures: " + str(e))
                #Bye()

            # Reset flag to False
            reconnection = False

        else:
            LOG.error(" - Access denied to Iotronic.") #: " + str(w_msg.message))
            Bye()


    except exception.ApplicationError as e:
        LOG.error(" - Iotronic Connection RPC error: " + str(e) )
        # Iotronic is offline the board can not call the "stack4things.connection" RPC
        # The board will disconnect from WAMP agent and retry later
        reconnection = True
        session.disconnect()


    except Exception as e:
        LOG.warning("Iotronic board connection error: " + str(e))
        #Bye()



class WampFrontend(ApplicationSession):
    """Function to manage the WAMP connection events.

    """

    @inlineCallbacks
    def onJoin(self, details):

        # LIGHTNING-ROD STATE:
        # - REGISTRATION STATE: the first connection to Iotronic
        # - FIRST CONNECTION: the board become operative after registration
        # - LIGHTNING-ROD BOOT: the first connection to WAMP after Lightning-rod starting
        # - WAMP RECOVERY: when the established WAMP connection fails

        global reconnection

        # reconnection flag is False when the board is:
        # - LIGHTNING-ROD BOOT
        # - REGISTRATION STATE
        # - FIRST CONNECTION
        #
        # reconnection flag is True when the board is:
        # - WAMP RECOVERY

        global SESSION
        SESSION = self

        board.session = self
        board.session_id = details.session
        # LOG.debug(" - session: " + str(details))

        LOG.info(" - Joined in WAMP-Agent:")
        LOG.info("   - wamp agent: " + str(board.agent))
        LOG.info("   - session ID: " + str(details.session))

        if reconnection is False:

            if board.uuid is None:

                ######################
                # REGISTRATION STATE #
                ######################

                # If in the LR configuration file there is not the Board UUID specified it means
                # the board is a new one and it has to call Iotronic in order to complete the registration

                try:

                    LOG.info(" - Board needs to be registered to Iotronic.")

                    rpc = u'stack4things.register'

                    with timeoutRPC(seconds=3, action=rpc):

                        res = yield self.call(rpc, code=board.code, session=details.session)

                    w_msg = WM.deserialize(res)

                    # LOG.info(" - Board registration result: \n" + json.loads(w_msg.message, indent=4))

                    if w_msg.result == WM.SUCCESS:

                        LOG.info("Registration authorized by Iotronic:\n" + str(w_msg.message))

                        # the message field contains the board configuration to load
                        board.setConf(w_msg.message)

                        # We need to disconnect the client from the registration-agent in
                        # order to reconnect to the WAMP agent assigned by Iotronic at the provisioning stage
                        LOG.info("\n\nDisconnecting from Registration Agent to load new settings...\n\n")
                        self.disconnect()

                    else:
                        LOG.error("Registration denied by Iotronic: " + str(w_msg.message))
                        Bye()

                except exception.ApplicationError as e:
                    LOG.error("IoTronic registration error: " + str(e))
                    # Iotronic is offline the board can not call the "stack4things.connection" RPC
                    # The board will disconnect from WAMP agent and retry later
                    reconnection = True # TO ACTIVE BOOT CONNECTION RECOVERY MODE
                    self.disconnect()

                except Exception as e:
                    LOG.warning(" - Board registration call error: {0}".format(e))
                    Bye()

            else:


                if board.status == "registered":
                    ####################
                    # FIRST CONNECTION #
                    ####################

                    # In this case we manage the first reconnection after the registration stage:
                    # at this stage Lightining-rod sets its status to "operative" completing the provisioning
                    # and configuration stage.
                    LOG.info("\n\n\nBoard is becoming operative...\n\n\n")
                    board.updateStatus("operative")
                    board.loadSettings()
                    IotronicLogin(board, self, details)

                elif board.status == "operative":
                    ######################
                    # LIGHTNING-ROD BOOT #
                    ######################

                    # After join to WAMP agent, Lightning-rod will:
                    # - authenticate to Iotronic
                    # - load the enabled modules

                    # The board will keep at this tage until it will succeed to connect to Iotronic.
                    IotronicLogin(board, self, details)

                else:
                    LOG.error("Wrong board status '"+board.status+"'.")
                    Bye()


        else:

            #################
            # WAMP RECOVERY #
            #################

            LOG.info("Board connection recovery...")

            try:

                rpc = str(board.agent) + u'.stack4things.connection'

                with timeoutRPC(seconds=3, action=rpc):
                    res = yield self.call(rpc, uuid=board.uuid, session=details.session)

                w_msg = WM.deserialize(res)

                if w_msg.result == WM.SUCCESS:

                    LOG.info("Access granted to Iotronic.") #: " + str(w_msg.message))

                    # LOADING BOARD MODULES
                    # If the board is in WAMP connection recovery state
                    # we need to register again the RPCs of each module
                    try:

                        yield moduleReloadInfo(self, details)

                        # Reset flag to False
                        reconnection = False

                        LOG.info("WAMP Session Recovered!")

                        LOG.info("\n\nListening...\n\n")


                    except Exception as e:
                        LOG.warning("WARNING - Could not register procedures: {0}".format(e))
                        Bye()

                else:
                    LOG.error("Access denied to Iotronic: " + str(w_msg.message))
                    Bye()


            except exception.ApplicationError as e:
                LOG.error("IoTronic connection error: " + str(e))
                # Iotronic is offline the board can not call the "stack4things.connection" RPC
                # The board will disconnect from WAMP agent and retry later
                reconnection = False # TO ACTIVE WAMP CONNECTION RECOVERY MODE
                self.disconnect()

            except Exception as e:
                LOG.warning("Board connection error after WAMP recovery: {0}".format(e))
                Bye()

    @inlineCallbacks
    def onLeave(self, details):
        LOG.warning('WAMP Session Left: {}'.format(details))


class WampClientFactory(websocket.WampWebSocketClientFactory, ReconnectingClientFactory):

    def clientConnectionFailed(self, connector, reason):
        LOG.warning("WAMP Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):

        LOG.warning("WAMP Connection Lost.")

        global reconnection

        LOG.warning("WAMP status:  board = " + str(board.status) + " - reconnection = " + str(reconnection))

        if board.status == "operative" and reconnection is False:

            #################
            # WAMP RECOVERY #
            #################

            # we need to recover wamp session and
            # we set reconnection flag to True in order to activate
            # the RPCs module registration procedure for each module

            reconnection = True

            LOG.info("Reconnecting to " + str(connector.getDestination().host) + ":" + str(connector.getDestination().port))
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        elif board.status == "operative" and reconnection is True:

            ######################
            # LIGHTNING-ROD BOOT #
            ######################

            # At this stage if the reconnection flag was set to True
            # it means that we forced the reconnection procedure
            # because of the board is not able to connect to Iotronic
            # calling "stack4things.connection" RPC... Iotronic is offline!

            # We need to reset the recconnection flag to False in order to
            # do not enter in RPCs module registration procedure...
            # At this stage the board tries to reconnect to Iotronic until it will come online again.
            reconnection = False

            LOG.info("Connecting to " + str(connector.getDestination().host) + ":" + str(connector.getDestination().port))
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        elif (board.status == "registered"):

            # REGISTRATION STATE
            LOG.debug("\n\nReconnecting after registration...\n\n")

            # LR load the new configuration and gets the new WAMP-Agent
            board.loadSettings()

            # LR has to connect to the assigned WAMP-Agent
            wampConnect(board.wamp_config)

        else:
            LOG.error("Reconnection wrong status!")


def wampConnect(wamp_conf):

    component_config = types.ComponentConfig(realm=unicode(wamp_conf['realm']))
    session_factory = wamp.ApplicationSessionFactory(config=component_config)
    session_factory.session = WampFrontend

    transport_factory = WampClientFactory(session_factory, url=wamp_conf['url'])
    transport_factory.autoPingInterval = 5
    transport_factory.autoPingTimeout = 5

    connector = websocket.connectWS(transport_factory)

    LOG.info("WAMP status:")
    #LOG.info(" - establishing connection to " + str(connector.getDestination()))
    addr = str(connector.getDestination().host)
    LOG.info(" - establishing connection to " + addr)

    try:
        socket.inet_pton(socket.AF_INET, addr)
        #LOG.info(" - IP validated!")
    except socket.error as err:
        LOG.error(" - IP address validation error: " + str(err))
        Bye()



class WampManager(object):

    def __init__(self, wamp_conf):

        wampConnect(wamp_conf)

    def start(self):
        LOG.info(" - starting WAMP server...")
        reactor.run()

        """
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
        """
    def stop(self):
        LOG.info("Stopping WAMP-agent server...")
        reactor.stop()
        LOG.info("WAMP server stopped!")


def Bye():
    LOG.info("Bye!")
    os._exit(1)


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

        Bye()


