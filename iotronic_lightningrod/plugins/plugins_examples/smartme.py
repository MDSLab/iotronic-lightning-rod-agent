# Copyright 2017 MDSLAB - University of Messina
#    All Rights Reserved.
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

from iotronic_lightningrod.devices.gpio import yun
from iotronic_lightningrod.plugins import Plugin

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

# User imports
import datetime
import math
import time

ADCres = 1023.0
Beta = 3950
Kelvin = 273.15
Rb = 10000
Ginf = 120.6685

# User global variables
#board_uuid = ebec5fe9-cfed-5c78-ccb3-33978a6a064d Ingegneria-dev-14
resource_id = "fccd5470-e5ed-4350-9aae-4419dd86264c"  # temperature resource id
action_URL = "http://smartme-data.unime.it/api/3/action/datastore_upsert"

api_key = '22c5cfa7-9dea-4dd9-9f9d-eedf296852ae'
headers = {"Content-Type": "application/json", 'Authorization': "" + api_key + ""}

polling_time = 10


class Worker(Plugin.Plugin):
    def __init__(self, name, plugin_conf=None):
        super(Worker, self).__init__(name, plugin_conf)

    def run(self):

        device = yun.YunGpio()

        while (self._is_running):

            m_timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

            voltage = device._readVoltage("A0")

            Rthermistor = float(Rb) * (float(ADCres) / float(voltage) - 1)
            rel_temp = float(Beta) / (math.log(float(Rthermistor) * float(Ginf)))
            temp = rel_temp - Kelvin

            m_value = str(temp)

            ckan_data = '{"resource_id":"' + str(resource_id) + '", "method":"insert", ' \
                '"records":[{"Latitude":"38.2597708","Altitude":"0","Longitude":"15.5966863",' \
                '"Temperature":"' + m_value + '","Date":"' + m_timestamp + '"}]}'

            self.sendRequest(url=action_URL, headers=headers, data=ckan_data, verbose=False)

            LOG.info("\nMEASURE SENT TO CKAN: \n" + ckan_data)

            time.sleep(polling_time)
