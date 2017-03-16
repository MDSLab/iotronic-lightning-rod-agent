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

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

PLUGINS_THRS = {}
PLUGINS_CONF_FILE = iotronic_home + "/plugins.json"


def getFuncName():
    return inspect.stack()[1][3]


def createPlugin(plugin_name, code):

    ser = PluginSerializer.ObjectSerializer()
    loaded = ser.deserialize_entity(code)   # loaded = ser.deserialize_entity({}, code)
    LOG.debug("- plugin loaded code:\n" + loaded)
    LOG.debug("- plugin creation starting...")

    plugin_path = iotronic_home + "/plugins/" + plugin_name + "/"
    plugin_filename = plugin_path + plugin_name + ".py"

    if not os.path.exists(plugin_path):
        os.makedirs(plugin_path)

    with open(plugin_filename, "w") as pluginfile:
        pluginfile.write(loaded)

    plugins_conf = loadPluginsConf()

    plugins_conf['plugins'][plugin_name] = {}
    plugins_conf['plugins'][plugin_name]['onboot'] = False   # TEMPORARY
    plugins_conf['plugins'][plugin_name]['callable'] = False   # TEMPORARY


    with open(PLUGINS_CONF_FILE, 'w') as f:
        json.dump(plugins_conf, f, indent=4)


def deletePlugin(plugin_name):
    # Delete plugin folder and files if they exist

    try:
        plugin_path = iotronic_home + "/plugins/" + plugin_name + "/"
        shutil.rmtree(plugin_path, ignore_errors=False, onerror=None)
    except Exception as err:
        LOG.error("Removing plugin's files error in " + plugin_path + ": " + str(err))

    # Remove from plugins.json file its configuration
    plugins_conf = loadPluginsConf()

    if plugin_name in plugins_conf['plugins']:
        del plugins_conf['plugins'][plugin_name]

        with open(PLUGINS_CONF_FILE, 'w') as f:
            json.dump(plugins_conf, f, indent=4)

        if plugin_name in PLUGINS_THRS:
            del PLUGINS_THRS[plugin_name]

        result = "Plugin " + plugin_name + " removed!"
        LOG.info(result)

    else:
        result = "Plugin " + plugin_name + " already removed!"
        LOG.warning(result)

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


class PluginManager(Module.Module):

    def __init__(self, board, session):

        # Module declaration
        super(PluginManager, self).__init__("PluginManager", board)

        # Creation of plugins.json configuration file
        createPluginsConf()

    def finalize(self):
        # Reboot boot enabled plugins
        self.RebootPlugins()

    def PluginInject(self, plugin_name, code):
        # 1. get Plugin files
        # 2. deserialize files
        # 3. store files
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")
        LOG.info(" - plugin name: " + plugin_name)
        LOG.debug(" - plugin dumped code:\n" + code)

        t = threading.Thread(target=createPlugin, args=(plugin_name, code,))

        t.start()

        yield t.join()

        result = rpc_name + " result: INJECTED"
        LOG.info(result)

        returnValue(result)

    def PluginStart(self, plugin_name, plugin_conf=None):

        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")

        if (plugin_name in PLUGINS_THRS) and (PLUGINS_THRS[plugin_name].isAlive()):
            LOG.warning(" - Plugin " + plugin_name + " already started!")

            result = rpc_name + " result: ALREADY STARTED!"

            returnValue(result)

        else:

            plugin_home = iotronic_home + "/plugins/" + plugin_name
            plugin_filename = plugin_home + "/" + plugin_name + ".py"
            plugin_conf_file = plugin_home + "/" + plugin_name + ".json"

            LOG.debug(" - Plugin path: " + plugin_filename)
            LOG.debug(" - Plugin Config path: " + plugin_conf_file)

            if plugin_conf != None:
                with open(plugin_conf_file, 'w') as f:
                    json.dump(plugin_conf, f, indent=4)

                with open(plugin_conf_file) as conf:
                    plugin_conf_loaded = json.load(conf)

            if os.path.exists(plugin_filename):



                task = imp.load_source("plugin", plugin_filename)

                LOG.info("Plugin " + plugin_name + " imported!")

                if plugin_conf != None:
                    worker = task.Worker(plugin_name, plugin_conf_loaded)
                else:
                    worker = task.Worker(plugin_name)

                PLUGINS_THRS[plugin_name] = worker
                LOG.debug("Starting plugin " + str(worker))

                yield worker.start()

                result = worker.complete(rpc_name, "STARTED")

                returnValue(result)

            else:
                result = rpc_name + " - ERROR " + plugin_filename + " does not exist!"
                LOG.warning(result)
                returnValue(result)

    def PluginStop(self, plugin_name):
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")

        if plugin_name in PLUGINS_THRS:

            worker = PLUGINS_THRS[plugin_name]
            LOG.info(" - Stopping plugin " + str(worker))

            if worker.isAlive():

                yield worker.stop()

                del PLUGINS_THRS[plugin_name]

                result = worker.complete(rpc_name, "KILLED")

            else:
                result = rpc_name + " - ERROR - plugin " + plugin_name + " is not running!"
                LOG.warning(result)

        else:
            result = rpc_name + " - ERROR " + plugin_name + " is not instantiated!"
            LOG.warning(result)

        returnValue(result)

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

            LOG.debug(" - Plugin path: " + plugin_filename)
            LOG.debug(" - Plugin Config path: " + plugin_conf_file)

            if plugin_conf != None:
                with open(plugin_conf_file, 'w') as f:
                    json.dump(plugin_conf, f, indent=4)

                with open(plugin_conf_file) as conf:
                    plugin_conf_loaded = json.load(conf)

            if os.path.exists(plugin_filename):

                try:

                    task = imp.load_source("plugin", plugin_filename)

                    LOG.info("Plugin " + plugin_name + " imported!")

                    th_result = Queue()

                    LOG.info("Plugin configuration:\n" + str(plugin_conf_loaded))

                except Exception as err:
                    result = yield "Error importing plugin " + plugin_filename + ": " + str(err)
                    LOG.error(result)
                    returnValue(result)


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

                    result = worker.complete(rpc_name, response)

                    returnValue(result)

                except Exception as err:
                    result = yield "Error spawning plugin " + plugin_filename + ": " + str(err)
                    LOG.error(result)
                    returnValue(result)

            else:
                result = rpc_name + " - ERROR " + plugin_filename + " does not exist!"
                LOG.warning(result)
                returnValue(result)



    def PluginRemove(self, plugin_name):
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED for " + plugin_name + " plugin:")

        result = yield deletePlugin(plugin_name)

        returnValue(result)

    def RebootPlugins(self):
        rpc_name = getFuncName()
        LOG.info("RPC " + rpc_name + " CALLED:\n")
        LOG.info("REBOOTING ENABLED PLUGINS:")

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
