# Copyright 2014 University of Messina (UniMe)
#
# Authors: Nicola Peditto <npeditto@unime.it>, Fabio Verboso <fverboso@unime.it>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
Created on 19/12/2016

@authors: Nicola Peditto <npeditto@unime.it>, Fabio Verboso <fverboso@unime.it>
'''

__author__="MDSLAB Team"

import abc

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class Module(object):
    """
    Base class for each s4t LR module.
    """
    
    __metaclass__ = abc.ABCMeta
    
 
    def __init__(self, name, session):
        '''
        Costructor
        @param    probe    probe object 
        '''
       
        self.name = name
	self.session = session

	LOG.info("Loading module " + self.name + "...")
            


       
    """
    @abc.abstractmethod
    def test(self):
        #Main plugin method.
        
    """




