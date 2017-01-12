# Copyright 2016 University of Messina (UniMe)
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


import threading
import abc
import os


class Plugin(threading.Thread):
    
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, name):
      
        threading.Thread.__init__(self)
        
        #self.setDaemon(1)
        
        self.name = name
        
        self.setName("Plugin " + str(self.name)) #Set thread name 

        
    def run(self):
        """
        Metodo run da ridefinire nel file del task
        """
        pass
    
    def Done(self):
        pass
            
    def Status(self):
        return status
    
    def setStatus(self, status):
	pass
    
        
