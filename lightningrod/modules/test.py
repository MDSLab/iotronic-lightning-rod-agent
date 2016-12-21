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
Created on 18/lug/2014

@authors: Nicola Peditto <npeditto@unime.it>, Fabio Verboso <fverboso@unime.it>
'''

from lightningrod.modules import Module
from stevedore import named

from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn.twisted.util import sleep


class Test(Module.Module):


    def __init__(self, session):
        
        super(Test, self).__init__()
        
	self.name = "Test"
	self.session = session
        print "Starting module " + self.name + "..."

      
    def test_function(self):
	import random
	s = random.uniform(0.5, 1.5)
	yield sleep(s)
	result = "DEVICE test result: TEST!"
	print result
	returnValue(result)

      

                


