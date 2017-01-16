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


from autobahn.twisted.util import sleep
from lightningrod.config import entry_points_name
from lightningrod.modules import Module
import pkg_resources
from six import moves
from stevedore import extension
import sys
from twisted.internet.defer import returnValue

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


def refresh_stevedore(namespace=None):
    """Trigger reload of entry points.

    Useful to have dynamic loading/unloading of stevedore modules.
    """
    # NOTE(sheeprine): pkg_resources doesn't support reload on python3 due to
    # defining basestring which is still there on reload hence executing
    # python2 related code.
    try:
        del sys.modules['pkg_resources'].basestring
    except AttributeError:
        # python2, do nothing
        pass
    # Force working_set reload
    moves.reload_module(sys.modules['pkg_resources'])
    # Clear stevedore cache
    cache = extension.ExtensionManager.ENTRY_POINT_CACHE
    if namespace:
        if namespace in cache:
            del cache[namespace]
    else:
        cache.clear()


class Utility(Module.Module):

    def __init__(self, session):

        super(Utility, self).__init__("Utility", session)

    def hello(self, client_name, message):
        import random
        s = random.uniform(0.5, 3.0)
        yield sleep(s)
        result = "Hello by board to Conductor " + client_name + \
            " that said me " + message + " - Time: " + '%.2f' % s
        # result = yield "Hello by board to Conductor "+client_name+" that said
        # me "+message
        LOG.info("DEVICE hello result: " + str(result))

        returnValue(result)

    def add(self, x, y):
        c = yield x + y
        LOG.info("DEVICE add result: " + str(c))
        returnValue(c)

    def plug_and_play(self, new_module, new_class):

        LOG.info("LR modules loaded:\n\t" + new_module)

        # Updating entry_points
        with open(entry_points_name, 'a') as entry_points:
            entry_points.write(
                new_module +
                '= lightningrod.modules.' + new_module + ':' + new_class)

            # Reload entry_points
            refresh_stevedore('s4t.modules')
            LOG.info("New entry_points loaded!")

        # Reading updated entry_points
        named_objects = {}
        for ep in pkg_resources.iter_entry_points(group='s4t.modules'):
            named_objects.update({ep.name: ep.load()})

        yield named_objects

        self.session.disconnect()

        returnValue(str(named_objects))
