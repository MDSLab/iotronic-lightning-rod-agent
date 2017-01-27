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
        with open(iotronic_home + '/settings.json') as settings:
            lr_settings = json.load(settings)

        return lr_settings

    def loadSettings(self):

        self.config = self.loadConf()

        self.node_conf = self.config['config']['node']
        self.uuid = self.node_conf['uuid']
        self.token = self.node_conf['token']

        LOG.debug('Node settings:')
        LOG.debug(' - token: ' + self.token)
        LOG.debug(' - uuid: ' + self.uuid)

        self.getWampAgent(self.config)

    def getWampAgent(self, config):

        try:
            self.wamp = config['config']['iotronic']['main-agent']
            LOG.info('Wamp Agent settings:')

        except Exception:
            self.wamp = config['config']['iotronic']['registration-agent']
            LOG.info('Registration Agent settings:')

        LOG.debug(' - url: ' + self.wamp['url'])
        LOG.debug(' - realm: ' + self.wamp['realm'])