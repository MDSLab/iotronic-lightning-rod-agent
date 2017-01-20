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


import abc
import httplib2
from iotronic_lightningrod.config import package_path
import json
import six
import threading
from twisted.internet.defer import inlineCallbacks


from oslo_log import log as logging
LOG = logging.getLogger(__name__)


@inlineCallbacks
def sendNotification(session, msg=None):
    try:
        res = yield session.call(u'register_board')
        LOG.info("NOTIFICATION " + str(res))
    except Exception as e:
        LOG.warning("NOTIFICATION error: {0}".format(e))


@six.add_metaclass(abc.ABCMeta)
class Plugin(threading.Thread):
    # __metaclass__ = abc.ABCMeta

    def __init__(self, name, session):
        threading.Thread.__init__(self)
        # self.setDaemon(1)
        self.setName("Plugin " + str(self.name))  # Set thread name

        self.name = name
        self.path = package_path + "/plugins/" + self.name + ".py"
        self.status = "None"
        self.session = session

        self.setStatus("INITED")

    def run(self):
        """Metodo run da ridefinire nel file del plugin

        """
        pass

    def Done(self):
        self.setStatus("COMPLETED")
        sendNotification(self.session)
        self.checkStatus()

    def checkStatus(self):
        LOG.debug("Plugin " + self.name + " check status: " + self.status)
        return self.status

    def setStatus(self, status):
        self.status = status
        LOG.debug("Plugin " + self.name + " changed status: " + self.status)

    def sendRequest(self, url=None, headers={}, data=None, verbose=False):
        http = httplib2.Http()
        headers = headers
        response, send = http.request(url, 'POST', headers=headers, body=data)
        result = json.dumps(response, sort_keys=True, indent=4, separators=(',', ': '))
        if verbose:
            LOG.debug("\nREST REQUEST:\n" + send)
            LOG.debug("\nREST RESPONSE:\n" + result)
        return send
