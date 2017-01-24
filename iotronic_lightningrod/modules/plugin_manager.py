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


def createPlugin(plugin_name, code):

    ser = PluginSerializer.ObjectSerializer()
    loaded = ser.deserialize_entity({}, code)
    LOG.debug("- plugin loaded code:\n" + loaded)
    LOG.debug("- plugin creation starting...")
    plugin_path = iotronic_home + "plugins/" + plugin_name + ".py"

    with open(plugin_path, "w") as pluginfile:
        pluginfile.write(loaded)


class PluginManager(Module.Module):

    def __init__(self, session):

        self.session = session

        # Module declaration
        super(PluginManager, self).__init__("PluginManager", self.session)

    def test_plugin(self):
        LOG.info(" - test_plugin CALLED...")

        plugin_name = "plugin_ZERO"
        LOG.debug("Plugins path: " + package_path)

        path = package_path + "/plugins/" + plugin_name + ".py"

        if os.path.exists(path):

            LOG.info("Plugin PATH: " + path)

            task = imp.load_source("plugin", path)
            LOG.info("Plugin " + plugin_name + " imported!")

            worker = task.Worker(plugin_name, self.session)
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
        LOG.info("- PluginInject CALLED:")
        LOG.info(" - plugin name: " + plugin_name)
        LOG.info(" - plugin dumped code:\n" + code)

        t = threading.Thread(target=createPlugin, args=(plugin_name, code,))
        t.start()

        yield t.join()

        result = "PluginInject result: injected!\n"
        LOG.info(result)

        returnValue(result)

    def PluginStart(self, plugin_name):
        LOG.info("- PluginStart CALLED...")

        LOG.debug(" - Plugins path: " + package_path)

        plugin_path = iotronic_home + "plugins/" + plugin_name + ".py"

        if os.path.exists(plugin_path):

            task = imp.load_source("plugin", plugin_path)
            LOG.info("Plugin " + plugin_name + " imported!")

            worker = task.Worker(plugin_name, self.session)
            worker.setStatus("STARTED")
            result = worker.checkStatus()

            yield worker.start()

            returnValue(result)

        else:
            LOG.warning("ERROR il file " + plugin_path + " non esiste!")

    def PluginStop(self):
        LOG.info(" - PluginStop CALLED...")
        yield makeNothing()
        result = "plugin result: PluginStop!\n"
        LOG.info(result)
        returnValue(result)

    def PluginCall(self):
        LOG.info(" - PluginCall CALLED...")
        yield makeNothing()
        result = "plugin result: PluginCall!\n"
        LOG.info(result)
        returnValue(result)

    def PluginRemove(self):
        LOG.info(" - PluginRemove CALLED...")
        yield makeNothing()
        result = "plugin result: PluginRemove!\n"
        LOG.info(result)
        returnValue(result)
