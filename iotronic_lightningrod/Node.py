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

from datetime import datetime
# from dateutil.tz import tzlocal
import json

from iotronic_lightningrod.config import iotronic_home

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

SETTINGS = iotronic_home + '/settings.json'


class Node(object):

    def __init__(self):
        self.iotronic_config = {}

        self.node_config = {}
        self.name = None
        self.type = None
        self.status = None
        self.uuid = None
        self.token = None
        self.agent = None
        self.mobile = None
        self.session = None

        self.wamp_config = None
        self.extra = {}

        self.loadSettings()

    def loadConf(self):
        '''This method loads the JSON configuraton file: settings.json.

        '''

        try:

            with open(SETTINGS) as settings:
                lr_settings = json.load(settings)

        except Exception as err:
            LOG.error("Parsing error in " + SETTINGS + ": " + str(err))
            lr_settings = None

        return lr_settings

    def loadSettings(self):
        '''This method gets and sets the Node attributes from the conf file.

        '''

        self.iotronic_config = self.loadConf()

        try:
            # STATUS OPERATIVE
            self.node_config = self.iotronic_config['iotronic']['node']
            self.uuid = self.node_config['uuid']
            self.token = self.node_config['token']
            self.name = self.node_config['name']
            self.status = self.node_config['status']
            self.type = self.node_config['type']
            self.mobile = self.node_config['mobile']
            self.extra = self.node_config['extra']
            self.created_at = self.node_config['created_at']
            self.updated_at = self.getTimestamp()  # self.node_config['updated_at']

            self.extra = self.iotronic_config['iotronic']['extra']

            LOG.info('Node settings:')
            LOG.info(' - token: ' + str(self.token))
            LOG.info(' - uuid: ' + str(self.uuid))
            print('Node settings:')
            """
            print(' - token: ' + str(self.token))
            print(' - uuid: ' + str(self.uuid))
            """

            self.getWampAgent(self.iotronic_config)

            print(json.dumps(self.node_config, indent=4))

        except Exception:
            # STATUS REGISTERED
            self.token = self.node_config['token']
            LOG.info('First registration node settings: ')
            LOG.info(' - token: ' + str(self.token))
            self.getWampAgent(self.iotronic_config)

    def getWampAgent(self, config):
        '''This method gets and sets the WAMP Node attributes from the conf file.

        '''
        try:
            self.wamp_config = config['iotronic']['wamp']['main-agent']
            LOG.info('Wamp Agent settings:')

        except Exception:
            if (self.status is None) | (self.status == "registered"):
                self.wamp_config = config['iotronic']['wamp']['registration-agent']
                LOG.info('Registration Agent settings:')
            else:
                LOG.error("Wamp agent configuration is wrong! "
                          "Please check settings.json WAMP configuration...Bye!")
                exit()

        LOG.debug(' - url: ' + str(self.wamp_config['url']))
        LOG.debug(' - realm: ' + str(self.wamp_config['realm']))

    def setConf(self, conf):
        print("NEW CONFIGURATION:\n" + str(json.dumps(conf, indent=4)))

        with open(SETTINGS, 'w') as f:
            json.dump(conf, f, indent=4)

        # Reload configuration
        self.loadSettings()

    def updateStatus(self, status):
        self.iotronic_config['iotronic']['node']["status"] = status

        self.iotronic_config['iotronic']['node']["updated_at"] = self.updated_at

        with open(SETTINGS, 'w') as f:
            json.dump(self.iotronic_config, f, indent=4)

    def getTimestamp(self):
        # datetime.now(tzlocal()).isoformat()
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

    def setUpdateTime(self):
        self.iotronic_config['iotronic']['node']["updated_at"] = self.updated_at

        with open(SETTINGS, 'w') as f:
            json.dump(self.iotronic_config, f, indent=4)
