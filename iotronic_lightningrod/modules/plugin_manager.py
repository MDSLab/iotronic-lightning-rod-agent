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


import imp
import inspect
from iotronic_lightningrod.modules import Module
import os
import threading
from twisted.internet.defer import returnValue

from oslo_log import log as logging

LOG = logging.getLogger(__name__)

from iotronic_lightningrod.config import iotronic_home
from iotronic_lightningrod.config import package_path
from iotronic_lightningrod.plugins import PluginSerializer


def makeNothing():
    pass


def whoami():
    return inspect.stack()[1][3]


PLUGINS_THRS = {}


def createPlugin(plugin_name, code):

    ser = PluginSerializer.ObjectSerializer()
    #loaded = ser.deserialize_entity({}, code)
    loaded = ser.deserialize_entity(code)
    LOG.debug("- plugin loaded code:\n" + loaded)
    LOG.debug("- plugin creation starting...")

    plugin_path = iotronic_home + "/plugins/" + plugin_name + "/"
    plugin_filename = plugin_path + plugin_name + ".py"

    if not os.path.exists(plugin_path):
        os.makedirs(plugin_path)

    with open(plugin_filename, "w") as pluginfile:
        pluginfile.write(loaded)


class PluginManager(Module.Module):

    def __init__(self, node, session):

        # Module declaration
        super(PluginManager, self).__init__("PluginManager", node)

    def test_plugin(self):
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")

        plugin_name = "plugin_ZERO"
        LOG.debug("Plugins path: " + package_path)

        path = package_path + "/plugins/" + plugin_name + ".py"

        if os.path.exists(path):

            LOG.info("Plugin PATH: " + path)

            task = imp.load_source("plugin", path)
            LOG.info("Plugin " + plugin_name + " imported!")

            worker = task.Worker(plugin_name)
            worker.setStatus("STARTED")
            result = worker.checkStatus()

            yield worker.start()

            returnValue(result)

        else:
            LOG.warning("ERROR il file " + path + " non esiste!")

    def PluginInject(self, plugin_name, code):
        # 1. get Plugin files
        # 2. deserialize files
        # 3. store files
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")
        LOG.info(" - plugin name: " + plugin_name)
        LOG.debug(" - plugin dumped code:\n" + code)

        t = threading.Thread(target=createPlugin, args=(plugin_name, code,))

        t.start()

        yield t.join()

        result = rpc_name + " result: INJECTED"
        LOG.info(result)

        returnValue(result)

    def PluginStart(self, plugin_name):
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")

        plugin_filename = iotronic_home + "/plugins/" + plugin_name + "/" + plugin_name + ".py"

        LOG.debug(" - Plugin path: " + plugin_filename)

        if os.path.exists(plugin_filename):

            task = imp.load_source("plugin", plugin_filename)
            LOG.info("Plugin " + plugin_name + " imported!")

            worker = task.Worker(plugin_name)

            PLUGINS_THRS[plugin_name] = worker
            LOG.debug("Starting plugin " + str(worker))

            yield worker.start()

            result = worker.complete(rpc_name, "STARTED")

            returnValue(result)

        else:
            LOG.warning("ERROR il file " + plugin_filename + " non esiste!")

    def PluginStop(self, plugin_name):
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")

        worker = PLUGINS_THRS[plugin_name]
        LOG.debug("Stopping plugin " + str(worker))

        yield worker.stop()

        result = worker.complete(rpc_name, "KILLED")

        returnValue(result)

    def PluginCall(self):
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")
        yield makeNothing()
        result = "plugin result: PluginCall!\n"
        LOG.info(result)
        returnValue(result)

    def PluginRemove(self):
        rpc_name = whoami()
        LOG.info("RPC " + rpc_name + " CALLED...")
        yield makeNothing()
        result = "plugin result: PluginRemove!\n"
        LOG.info(result)
        returnValue(result)
