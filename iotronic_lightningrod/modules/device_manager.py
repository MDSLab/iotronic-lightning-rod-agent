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
from iotronic_lightningrod.config import package_path
from iotronic_lightningrod.modules import Module
import os

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

# OSLO imports
from oslo_config import cfg

CONF = cfg.CONF


def makeNothing():
    pass


class DeviceManager(Module.Module):
    def __init__(self, session):

        self.session = session

        # Module declaration
        super(DeviceManager, self).__init__("DeviceManager", self.session)

        device_name = CONF.device.name

        path = package_path + "/devices/" + device_name + ".py"

        if os.path.exists(path):
            LOG.debug("Device module path: " + path)

            device_module = imp.load_source("device", path)

            LOG.info("Device " + device_name + " module imported!")

            device_module.System()

        else:
            LOG.warning("Device " + device_name + " not supported!")
