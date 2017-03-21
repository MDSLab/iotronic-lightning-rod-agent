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

from __future__ import absolute_import

from datetime import datetime
import imp
import inspect
import json
import os
import shutil
import threading
from twisted.internet.defer import returnValue

from Queue import Queue

from iotronic_lightningrod.config import iotronic_home
from iotronic_lightningrod.modules import Module
from iotronic_lightningrod.plugins import PluginSerializer
import iotronic_lightningrod.wampmessage as WM


from oslo_log import log as logging
LOG = logging.getLogger(__name__)

PLUGINS_THRS = {}
PLUGINS_CONF_FILE = iotronic_home + "/plugins.json"


def getFuncName():
    return inspect.stack()[1][3]



def deletePlugin(plugin_uuid):
    # Delete plugin folder and files if they exist

    try:
        plugin_path = iotronic_home + "/plugins/" + plugin_uuid + "/"
        shutil.rmtree(plugin_path, ignore_errors=False, onerror=None)
    except Exception as err:
        LOG.error("Removing plugin's files error in " + plugin_path + ": " + str(err))

    # Remove from plugins.json file its configuration
    plugins_conf = loadPluginsConf()

    if plugin_uuid in plugins_conf['plugins']:
        del plugins_conf['plugins'][plugin_uuid]

        with open(PLUGINS_CONF_FILE, 'w') as f:
            json.dump(plugins_conf, f, indent=4)

        if plugin_uuid in PLUGINS_THRS:
            del PLUGINS_THRS[plugin_uuid]

        result = "PluginRemove result: " + plugin_uuid + " removed!"
        LOG.info(" - "+result)

    else:
        result = "PluginRemove result:  " + plugin_uuid + " already removed!"
        LOG.warning(" - "+result)

    return result


def createPluginsConf():
    if not os.path.exists(PLUGINS_CONF_FILE):
        LOG.debug("plugins.json does not exist: creating...")
        plugins_conf = {'plugins': {}}
        with open(PLUGINS_CONF_FILE, 'w') as f:
            json.dump(plugins_conf, f, indent=4)


def loadPluginsConf():

    try:

        with open(PLUGINS_CONF_FILE) as settings:
            plugins_conf = json.load(settings)

    except Exception as err:
        LOG.error("Parsing error in " + PLUGINS_CONF_FILE + ": " + str(err))
        plugins_conf = None

    return plugins_conf


def getEnabledPlugins():
    enabledPlugins = []
    plugins_conf = loadPluginsConf()

    for plugin in plugins_conf['plugins']:
        enabled = plugins_conf['plugins'][plugin]['onboot']
        if enabled:
            enabledPlugins.append(plugin)

    LOG.info(" - Enabled plugins list: " + str(enabledPlugins))

    return enabledPlugins


def makeNothing():
    pass



class PluginManager(Module.Module):

    def __init__(self, board, session):

        # Module declaration
        super(PluginManager, self).__init__("PluginManager", board)

        # Creation of plugins.json configuration file
        createPluginsConf()


    def finalize(self):
        """

        :return:
        """
        # Reboot boot enabled plugins
        self.RebootPlugins()


    def PluginInject(self, plugin, onboot):
        """
        Plugin injection procedure:
         1. get Plugin files
         2. deserialize files
         3. store files

        :param plugin:
        :param onboot:
        :return:
        """


        rpc_name = getFuncName()

        try:

            plugin_name = plugin['name']
            plugin_uuid = plugin['uuid']
            code = plugin['code']
            callable = plugin['callable']

            LOG.info("RPC " + rpc_name + " for plugin " + plugin_name + " (" + plugin_uuid + ")")

            # Deserialize the plugin code received
            ser = PluginSerializer.ObjectSerializer()
            loaded = ser.deserialize_entity(code)
            # LOG.debug("- plugin loaded code:\n" + loaded)

            plugin_path = iotronic_home + "/plugins/" + plugin_uuid + "/"
            plugin_filename = plugin_path + plugin_uuid + ".py"

            # Plugin folder creation if does not exist
            if not os.path.exists(plugin_path):
                os.makedirs(plugin_path)

            # Plugin code file creation
            with open(plugin_filename, "w") as pluginfile:
                pluginfile.write(loaded)

            # Load plugins.json configuration file
            plugins_conf = loadPluginsConf()

            # Save plugin settings in plugins.json
            if plugin_uuid not in plugins_conf['plugins']:

                # It is a new plugin
                plugins_conf['plugins'][plugin_uuid] = {}
                plugins_conf['plugins'][plugin_uuid]['label'] = plugin_name
                plugins_conf['plugins'][plugin_uuid]['onboot'] = onboot
                plugins_conf['plugins'][plugin_uuid]['callable'] = callable
                plugins_conf['plugins'][plugin_uuid]['injected_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
                plugins_conf['plugins'][plugin_uuid]['updated_at'] = ""

                LOG.info("Plugin " + plugin_name + " created!")
                message = rpc_name + " result: INJECTED"


            else:
                # The plugin was already injected and we are updating it
                plugins_conf['plugins'][plugin_uuid]['label'] = plugin_name
                plugins_conf['plugins'][plugin_uuid]['onboot'] = onboot
                plugins_conf['plugins'][plugin_uuid]['callable'] = callable
                plugins_conf['plugins'][plugin_uuid]['updated_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

                LOG.info("Plugin " + str(plugin_name) + " updated!")
                message = rpc_name + " result: UPDATED"


            # Apply the changes to plugins.json
            with open(PLUGINS_CONF_FILE, 'w') as f:
                yield json.dump(plugins_conf, f, indent=4)


            LOG.info(" - " + message)
            w_msg = WM.WampSuccess(message)

            returnValue(w_msg.serialize())



        except Exception as e:
            message = "Plugin injection error: {0}".format(e)
            LOG.error(" - " + message)
            w_msg = WM.WampError(message)
            returnValue(w_msg.serialize())


    def PluginStart(self, plugin_uuid, plugin_conf=None):
        """
        RPC called to start an asynchronous plugin; it will run until the PluginStop RPC is called.

        :param plugin_uuid:
        :param plugin_conf:
        :return:
        """

        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_uuid + " plugin:")

        # Check if the plugin is running
        if (plugin_uuid in PLUGINS_THRS) and (PLUGINS_THRS[plugin_uuid].isAlive()):

            LOG.warning(" - Plugin " + plugin_uuid + " already started!")

            message = yield "ALREADY STARTED!"
            LOG.error(" - " + message)
            w_msg = WM.WampError(message)
            returnValue(w_msg.serialize())


        else:
            # Get python module path
            plugin_home = iotronic_home + "/plugins/" + plugin_uuid
            plugin_filename = plugin_home + "/" + plugin_uuid + ".py"
            plugin_conf_file = plugin_home + "/" + plugin_uuid + ".json"

            # Store input parameters of the plugin
            if plugin_conf != None:
                with open(plugin_conf_file, 'w') as f:
                    json.dump(plugin_conf, f, indent=4)

                with open(plugin_conf_file) as conf:
                    plugin_conf_loaded = json.load(conf)

            # Import plugin (as python module)
            if os.path.exists(plugin_filename):

                task = imp.load_source("plugin", plugin_filename)

                LOG.info(" - Plugin " + plugin_uuid + " imported!")


                if plugin_conf != None:
                    LOG.info("plugin with parameters:")
                    LOG.info(plugin_conf_loaded['message'])
                    worker = task.Worker(plugin_uuid, None, plugin_conf_loaded)
                else:
                    worker = task.Worker(plugin_uuid, None)

                PLUGINS_THRS[plugin_uuid] = worker
                LOG.debug(" - Starting plugin " + str(worker))

                yield worker.start()

                response = "STARTED"
                LOG.info(" - " + worker.complete(rpc_name, response))
                w_msg = WM.WampSuccess(response)
                returnValue(w_msg.serialize())

            else:
                message = yield rpc_name + " - ERROR " + plugin_filename + " does not exist!"
                LOG.error(" - " + message)
                w_msg = WM.WampError(message)
                returnValue(w_msg.serialize())



    def PluginStop(self, plugin_name):
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")

        if plugin_name in PLUGINS_THRS:

            worker = PLUGINS_THRS[plugin_name]
            LOG.info(" - Stopping plugin " + str(worker))

            if worker.isAlive():

                yield worker.stop()

                del PLUGINS_THRS[plugin_name]

                message = "KILLED" #worker.complete(rpc_name, "KILLED")
                LOG.info(" - " + worker.complete(rpc_name, message))
                w_msg = WM.WampSuccess(message)

            else:
                message = rpc_name + " - ERROR - plugin " + plugin_name + " is not running!"
                LOG.warning(" - " + message)
                w_msg = WM.WampError(message)

        else:
            message = yield rpc_name + " - ERROR " + plugin_name + " is not instantiated!"
            LOG.warning(" - " + message)
            w_msg = WM.WampError(message)


        returnValue(w_msg.serialize())



    def PluginCall(self, plugin_name, plugin_conf=None):

        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")


        if (plugin_name in PLUGINS_THRS) and (PLUGINS_THRS[plugin_name].isAlive()):
            LOG.warning(" - Plugin " + plugin_name + " already started!")

            result = rpc_name + " result: already started!"

            returnValue(result)

        else:

            plugin_home = iotronic_home + "/plugins/" + plugin_name
            plugin_filename = plugin_home + "/" + plugin_name + ".py"
            plugin_conf_file = plugin_home + "/" + plugin_name + ".json"

            #LOG.debug(" - Plugin path: " + plugin_filename)
            #LOG.debug(" - Plugin Config path: " + plugin_conf_file)

            if plugin_conf != None:
                with open(plugin_conf_file, 'w') as f:
                    json.dump(plugin_conf, f, indent=4)

                with open(plugin_conf_file) as conf:
                    plugin_conf_loaded = json.load(conf)

            if os.path.exists(plugin_filename):

                try:

                    task = imp.load_source("plugin", plugin_filename)

                    LOG.info(" - Plugin " + plugin_name + " imported!")

                    th_result = Queue()

                    LOG.info(" - Plugin configuration:\n" + str(plugin_conf_loaded))

                except Exception as err:
                    message = yield "Error importing plugin " + plugin_filename + ": " + str(err)
                    LOG.error(" - " + message)
                    w_msg = WM.WampError(message)
                    returnValue(w_msg.serialize())


                try:

                    if plugin_conf != None:
                        worker = task.Worker(plugin_name, th_result, plugin_conf_loaded)
                    else:
                        worker = task.Worker(plugin_name, th_result)

                    PLUGINS_THRS[plugin_name] = worker
                    LOG.debug("Executing plugin " + str(worker))

                    worker.start()

                    while th_result.empty():
                        pass

                    response = yield th_result.get()

                    message = response #worker.complete(rpc_name, response)
                    LOG.info(" - " + worker.complete(rpc_name, response))
                    w_msg = WM.WampSuccess(message)

                    returnValue(w_msg.serialize())


                except Exception as err:
                    message = yield "Error spawning plugin " + plugin_filename + ": " + str(err)
                    LOG.error(" - " + message)
                    w_msg = WM.WampError(message)
                    returnValue(w_msg.serialize())

            else:
                message = yield rpc_name + " - ERROR " + plugin_filename + " does not exist!"
                LOG.error(" - " + message)
                w_msg = WM.WampError(message)
                returnValue(w_msg.serialize())



    def PluginRemove(self, plugin_uuid):
        rpc_name = getFuncName()

        LOG.info("RPC " + rpc_name + " for plugin " + plugin_uuid)
        try:

            result = yield deletePlugin(plugin_uuid)

            message = result
            w_msg = WM.WampSuccess(message)
            returnValue(w_msg.serialize())

        except Exception as e:
            message = "Plugin removing error: {0}".format(e)
            LOG.error(message)
            w_msg = WM.WampError(message)
            returnValue(w_msg.serialize())



    def RebootPlugins(self):

        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED")
        LOG.info("Rebooting enabled plugins:")

        enabledPlugins = getEnabledPlugins()

        if enabledPlugins.__len__() == 0:
            LOG.info(" - No plugin to reboot!")

        for plugin in enabledPlugins:
            try:

                if (plugin in PLUGINS_THRS) and (PLUGINS_THRS[plugin].isAlive()):

                    LOG.info(" - Plugin " + plugin + " already started!")

                else:
                    LOG.info(" - Rebooting plugin " + plugin)

                    plugin_home = iotronic_home + "/plugins/" + plugin
                    plugin_filename = plugin_home + "/" + plugin + ".py"
                    plugin_conf_file = plugin_home + "/" + plugin + ".json"

                    if os.path.exists(plugin_filename):

                        task = imp.load_source("plugin", plugin_filename)

                        if os.path.exists(plugin_conf_file):
                            with open(plugin_conf_file) as conf:
                                plugin_conf_loaded = json.load(conf)

                            worker = task.Worker(plugin, plugin_conf_loaded)
                        else:
                            worker = task.Worker(plugin)

                        PLUGINS_THRS[plugin] = worker
                        LOG.info("   - Starting plugin " + str(worker))

                        worker.start()

                    else:
                        LOG.warning(" - ERROR il file " + plugin_filename + " non esiste!")

            except Exception as err:
                LOG.error(" - Error rebooting plugin " + plugin + ": " + str(err))



    def checkStatusPlugin(self, plugin_name):
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")

        if plugin_name in PLUGINS_THRS:

            worker = PLUGINS_THRS[plugin_name]

            if worker.isAlive():

                result = yield worker.complete(rpc_name, "ALIVE")

            else:
                result = yield worker.complete(rpc_name, "DEAD")

        else:

            result = rpc_name + " result for " + plugin_name + ": DEAD"
            yield LOG.warning(result)

        returnValue(result)
