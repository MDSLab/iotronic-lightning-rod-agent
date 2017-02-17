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


import time
from oslo_log import log as logging

from iotronic_lightningrod.devices.gpio import Gpio

LOG = logging.getLogger(__name__)

"""
MAPPING = {'104': 'D8',
           '105': 'D9',
           '106': 'D10',
           '107': 'D11',
           '114': 'D5',
           '115': 'D13',
           '116': 'D3',
           '117': 'D2',
           '120': 'D4',
           '122': 'D12',
           '123': 'D6'}
"""



class YunGpio(Gpio.Gpio):
    def __init__(self):
        super(YunGpio, self).__init__("yun")

        self.MAPPING = {'D8': '104',
           'D9': '105',
           'D10': '106',
           'D11': '107',
           'D5': '114',
           'D13': '115',
           'D3': '116',
           'D2': '117',
           'D4': '120',
           'D12': '122',
           'D6': '123'}

        LOG.info("Arduino YUN gpio module importing...")

    # Enable GPIO
    def EnableGPIO(self):
        #LOG.info(" - EnableGPIO CALLED...")

        with open('/sys/bus/iio/devices/iio:device0/enable', 'a') as f:
            f.write('1')

        result = "  - GPIO result: enabled!\n"
        LOG.info(result)

    def DisableGPIO(self):
        #LOG.info(" - DisableGPIO CALLED...")

        with open('/sys/bus/iio/devices/iio:device0/enable', 'a') as f:
            f.write('0')

        result = "  - GPIO result: disabled!\n"
        LOG.info(result)


    def setPIN(self, DPIN, value):
        with open('/sys/class/gpio/' + DPIN + '/value', 'a') as f:
            f.write(value)

    def _setGPIOs(self, Dpin, direction, value):
        """
            GPIO mapping on lininoIO
            -------------------------
            GPIO n.     OUTPUT
            104	        D8
            105	        D9
            106	        D10
            107	        D11
            114	        D5
            115	        D13
            116	        D3
            117	        D2
            120	        D4
            122	        D12
            123	        D6

        """
        with open('/sys/class/gpio/export', 'a') as f_export:
            f_export.write(self.MAPPING[Dpin])

        with open('/sys/class/gpio/D13/direction', 'a') as f_direction:
            f_direction.write(direction)

        with open('/sys/class/gpio/D13/value', 'a') as f_value:
            f_value.write(value)

        with open('/sys/class/gpio/D13/value') as f_value:
            result = "PIN " + Dpin + " value " + f_value.read()
            print result

        return result

    def _readVoltage(self, pin):
        with open("/sys/bus/iio/devices/iio:device0/in_voltage_" + pin + "_raw") as raw:
            voltage = raw.read()
            print "VOLTAGE: " + voltage

        return voltage

    def blinkLed(self):
        """ LED: 13. There is a built-in LED connected to digital pin 13.
        When the pin is HIGH value, the LED is on, when the pin is LOW, it's off.

        """
        with open('/sys/class/gpio/export', 'a') as f:
            f.write('115')

        with open('/sys/class/gpio/D13/direction', 'a') as f:
            f.write('out')

        with open('/sys/class/gpio/D13/value', 'a') as f:
            f.write('1')

        time.sleep(2)

        with open('/sys/class/gpio/D13/value', 'a') as f:
            f.write('0')