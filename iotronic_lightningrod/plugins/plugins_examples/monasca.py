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

from iotronic_lightningrod.plugins import Plugin
from iotronic_lightningrod.plugins import pluginApis as API

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

# User imports
import datetime
import json
import math
import time


# MONASCA imports and global variables
import monasca_agent.forwarder.api.monasca_api as mon
message_batch = []
import random
import os


# User global variables

sensors_list = [
    'temperature',
    'brightness'
]
position = None
SENSORS = {}
location = {}
THR_KILL = None
iotronic_ip = "212.1892.207.225"
hostname = os.uname()[1]
device = API.getBoardGpio()

# Sensors global parameters
# - Temperature Parameters
ADCres = 1023.0
Beta = 3950
Kelvin = 273.15
Rb = 10000
Ginf = 120.6685
latest_temp = None



def Temperature():

    try:
        voltage = device._readVoltage(SENSORS['temperature']['pin'])

        Rthermistor = float(Rb) * (float(ADCres) / float(voltage) - 1)
        rel_temp = float(Beta) / (math.log(float(Rthermistor) * float(Ginf)))
        temp = rel_temp - Kelvin

        # LOG.info("Temperature " + str(temp) + u" \u2103")

    except Exception as err:
        LOG.error("Error getting temperature: " + str(err))

    return temp


def Brightness():

    try:
        voltage = float(device._readVoltage(SENSORS['brightness']['pin']))

        ldr = (2500 / (5 - voltage * float(0.004887)) - 500) / float(3.3)

        LOG.info("Brightness: " + str(ldr) + " (lux)")

    except Exception as err:
        LOG.error("Error getting brightness: " + str(err))

    return ldr


def getMetric(metric):

    # Call Sensors Metrics: Temperature(), etc...
    m_value = str(globals()[metric.capitalize()]())

    #m_timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    m_timestamp = time.time()*1000

    if metric == 'temperature':
        LOG.info("Temperature " + str(m_value) + u" \u2103")

    data = {}
    data[metric.capitalize()] = m_value
    data["Date"] = str(m_timestamp)
    data = json.dumps(data)

    return data


def setSensorsLayout(params):
    for sensor in sensors_list:
        SENSORS[sensor] = {}
        SENSORS[sensor]['pin'] = params[sensor]['pin']
        SENSORS[sensor]['enabled'] = params[sensor]['enabled']


def InitSmartMeBoard(params):
    """This function init the SmartME board.

    In the SmartME Arduino YUN board this function enables the needed
    devices and set the needed parameters about sensors and location.

    :param params: plugin parameters to configure the board.

    """

    # get location
    global location
    location = API.getLocation()
    LOG.info(
        "Board location: \n"
        + json.dumps(location, indent=4, separators=(',', ': '))
    )

    # set devices
    try:

        device.EnableGPIO()

    except Exception as err:
        LOG.error("Error configuring devices: " + str(err))
        global THR_KILL
        THR_KILL = False

    # set up sensors
    setSensorsLayout(params)


class Worker(Plugin.Plugin):

    def __init__(self, uuid, name, q_result=None, params=None):
        super(Worker, self).__init__(
            uuid, name,
            q_result=q_result,
            params=params
        )

    def run(self):

        LOG.info("SmartME plugin starting...")

        global THR_KILL
        THR_KILL = self._is_running

        # Board initialization
        LOG.info("PARAMS list: " + str(self.params.keys()))



        LOG.info("Monasca API loading....")
        global message_batch
        agent_config = {
            'is_enabled': False,
            'max_measurement_buffer_size': -1,
            'disable_file_logging': False,
            'additional_checksd': '/usr/lib/monasca/agent/custom_checks.d',
            'user_domain_name': 'Default',
            'use_keystone': True,
            'num_collector_threads': 1,
            'statsd_log_file': '/var/log/monasca/agent/statsd.log',
            'syslog_host': None,
            'keystone_timeout': 20,
            'max_buffer_size': 1000,
            'syslog_port': None,
            'limit_memory_consumption': None,
            'backlog_send_rate': 1000,
            'project_domain_id': None,
            'autorestart': True,
            'log_level': 'DEBUG',
            'collector_restart_interval': 24,
            'listen_port': None,
            'check_freq': 30,
            'hostname': str(hostname),
            'log_to_syslog': False,
            'non_local_traffic': False,
            'version': '1.7.0',
            'service_type': None,
            'jmxfetch_log_file': '/var/log/monasca/agent/jmxfetch.log',
            'pool_full_max_retries': 4,
            'project_domain_name': 'Default',
            'username': 'mini-mon',
            'collector_log_file': '/var/log/monasca/agent/collector.log',
            'project_name': 'mini-mon',
            'region_name': None,
            'skip_ssl_validation': False,
            'forwarder_url': 'http://localhost:17123',
            'amplifier': 0,
            'insecure': False,
            'dimensions': {},
            'endpoint_type': None,
            'ca_file': None,
            'password': 'password',
            'sub_collection_warn': 6,
            'project_id': None,
            'user_domain_id': None,
            'url': 'http://'+ iotronic_ip +':8080/v2.0',
            'keystone_url': 'http://'+ iotronic_ip +':35357/v3',
            'forwarder_log_file': '/var/log/monasca/agent/forwarder.log',
            'write_timeout': 10,
            'log_to_event_viewer': False
        }
        endpoint = mon.MonascaAPI(agent_config)

        from iotronicclient import client as iotronic_client
        #iotronic_auth =
        #iotronic = iotronic_client.Client('1', "admin", "admin", "boston", )


        if len(self.params.keys()) != 0:

            InitSmartMeBoard(self.params)

            # Get polling time
            polling_time = float(self.params['polling'])
            LOG.info("Polling time: " + str(polling_time))

            LOG.info(
                "SENSORS: \n"
                + json.dumps(SENSORS, indent=4, separators=(',', ': '))
            )

            counter = 0

            while (self._is_running and THR_KILL):

                if sensors_list.__len__() != 0:

                    LOG.info("\n\n")

                    # Get metrics
                    for sensor in sensors_list:

                        if SENSORS[sensor]['enabled']:

                            if sensor == "temperature":

                                measure = json.loads(getMetric(sensor))
                                value = measure['Temperature']

                                if value >= 10.0:
                                    LOG.info(
                                        "ALERT - Temperature over threshold!")
                                    polling_time = 2.0

                            else:
                                measure = json.loads(getMetric(sensor))
                                value = measure['Brightness']

                            timestamp = measure['Date']

                            LOG.info(" - " + sensor + ": " + str(value) + " -  time: " + timestamp)

                            # SEND TO MONASCA
                            LOG.info("Sending metrics to Monasca...")
                            try:
                                msg = [{
                                    'tenant_id': None,
                                    'measurement':
                                        {
                                            'timestamp': int(timestamp),
                                            'dimensions': {'hostname': str(hostname)},
                                            'name': 's4t-' + sensor,
                                            'value': value, # random.uniform(500, 1000),
                                            'value_meta': None
                                        }
                                }]

                                message_batch.extend(msg)

                                #endpoint.post_metrics(message_batch)

                                #LOG.info("wrote {}".format(len(message_batch)))
                                message_batch = []


                            except Exception as e :
                                LOG.error('Error parsing body of Agent Input: ' + str(e))

                            """                            """

                    counter = counter + 1
                    LOG.info("Sample number: " + str(counter))











                    """
                    # GET TOKEN
                    
                    LOG.info("Getting Keystone token...")
                    keystone_pl = {
                        "auth": {
                            "identity": {
                                "methods": ["password"],
                                "password": {
                                    "user": {
                                        "name": "admin",
                                        "domain": {"id": "default"},
                                        "password": "admin"
                                    }
                                }
                            },
                            "scope": {
                                "project": {
                                    "name": "boston",
                                    "domain": {"id": "default"}
                                }
                            }
                        }
                    }

                    keystone_pl = json.dumps(keystone_pl)
                    headers = {
                        "Content-Type": "application/json"
                    }

                    # Get Keystone token for IoTronic API
                    key_resp, send = API.sendRequest(
                        url="http://212.189.207.225:35357/v3/auth/tokens",
                        action='POST',
                        headers=headers,
                        body=keystone_pl,
                        verbose=False
                    )

                    #LOG.info("KEYSTONE: " + str(key_resp))
                    token = key_resp['x-subject-token']
                    LOG.info("KEYSTONE TOKEN: " + str(token))


                    #GET board list:
                    LOG.info("Getting board list...")
                    iotronic_url = "http://212.189.207.225:1288"

                    bl_header = {
                        "X-Auth-Token": str(token)
                    }

                    bl_resp, send = API.sendRequest(
                        url=iotronic_url+'/v1/boards',
                        action='GET',
                        headers=bl_header,
                        verbose=False
                    )

                    #LOG.info("Board list resp: " + str(bl_resp))

                    LOG.info("Board list send: " + str(send))
                    """

















                    time.sleep(polling_time)

                else:
                    LOG.warning("No sensors!")
                    self._is_running = False
                    THR_KILL = self._is_running

            # Update the thread status: at this stage THR_KILL will be False
            THR_KILL = self._is_running

        else:
            LOG.error("No parameters provided!")
