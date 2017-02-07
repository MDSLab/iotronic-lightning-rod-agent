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

from iotronic_lightningrod.config import iotronic_home
import json

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class Node(object):

    def __init__(self):
        self.config = None
        self.node_conf = None
        self.uuid = None
        self.token = None
        self.wamp = None

        self.loadSettings()

    def loadConf(self):
        '''This method loads the JSON configuraton file: settings.json.

        '''

        try:

            with open(iotronic_home + '/settings.json') as settings:
                lr_settings = json.load(settings)

        except Exception as err:
            LOG.error("Parsing error in " + iotronic_home + "/settings.json : " + str(err))
            lr_settings = None

        return lr_settings

    def loadSettings(self):
        '''This method gets and sets the Node attributes from the conf file.

        '''

        self.config = self.loadConf()

        try:
            self.node_conf = self.config['config']['node']
            self.uuid = self.node_conf['uuid']
            self.token = self.node_conf['token']

            LOG.info('Node settings:')
            LOG.info(' - token: ' + str(self.token))
            LOG.info(' - uuid: ' + str(self.uuid))
            print('Node settings:')
            print(' - token: ' + str(self.token))
            print(' - uuid: ' + str(self.uuid))

            self.getWampAgent(self.config)

        except Exception as err:
            LOG.info('Node settings:')
            LOG.error(" - Configuration error in " + iotronic_home + "/settings.json: " + str(err))

    def getWampAgent(self, config):
        '''This method gets and sets the WAMP Node attributes from the conf file.

        '''
        try:
            self.wamp = config['config']['iotronic']['main-agent']
            LOG.info('Wamp Agent settings:')

        except Exception:
            self.wamp = config['config']['iotronic']['registration-agent']
            LOG.info('Registration Agent settings:')

        LOG.debug(' - url: ' + str(self.wamp['url']))
        LOG.debug(' - realm: ' + str(self.wamp['realm']))
