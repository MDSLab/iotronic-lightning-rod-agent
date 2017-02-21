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
import os
from twisted.internet.defer import inlineCallbacks

from iotronic_lightningrod.config import package_path
from iotronic_lightningrod.lightningrod import SESSION
from iotronic_lightningrod.modules import Module

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


def deviceWampRegister(dev_meth_list, node):
    LOG.info(" - " + node.type + " device registering RPCs:")

    for meth in dev_meth_list:

        if (meth[0] != "__init__"):  # We don't considere the __init__ method
            # LOG.info(" - " + str(meth[0]))
            rpc_addr = u'iotronic.' + node.uuid + '.' + meth[0]
            # LOG.debug(" --> " + str(rpc_addr))
            SESSION.register(inlineCallbacks(meth[1]), rpc_addr)

            LOG.info("  --> " + str(meth[0]) + " registered!")


class DeviceManager(Module.Module):

    def __init__(self, node, session):

        # Module declaration
        super(DeviceManager, self).__init__("DeviceManager", node)

        device_type = node.type

        path = package_path + "/devices/" + device_type + ".py"

        if os.path.exists(path):

            device_module = imp.load_source("device", path)

            LOG.info(" - Device " + device_type + " module imported!")

            device = device_module.System()

            dev_meth_list = inspect.getmembers(device, predicate=inspect.ismethod)

            deviceWampRegister(dev_meth_list, node)

        else:
            LOG.warning("Device " + device_type + " not supported!")

    def finalize(self):
        pass
