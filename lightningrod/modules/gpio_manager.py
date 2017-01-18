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


from lightningrod.modules import Module
from twisted.internet.defer import returnValue

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


def makeNothing():
    pass


class GpioManager(Module.Module):

    def __init__(self, session):

        self.session = session

        # Module declaration
        super(GpioManager, self).__init__("GpioManager", self.session)

        # Enable GPIO

    def EnableGPIO(self):
        LOG.info(" - EnableGPIO CALLED...")
        with open('/sys/bus/iio/devices/iio:device0/enable', 'a') as f:
            yield f.write('1')

        result = "GPIO result: enabled!\n"
        LOG.info(result)
        returnValue(result)

    def DisableGPIO(self):
        LOG.info(" - DisableGPIO CALLED...")
        with open('/sys/bus/iio/devices/iio:device0/enable', 'a') as f:
            yield f.write('0')

        result = "GPIO result: disabled!\n"
        LOG.info(result)
        returnValue(result)
