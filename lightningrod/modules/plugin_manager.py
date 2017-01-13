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


from lightningrod.modules import Module
from stevedore import named

from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn.twisted.util import sleep


import imp, os, sys


from oslo_log import log as logging
LOG = logging.getLogger(__name__)


def makeNothing():
    pass




class PluginManager(Module.Module):

    def __init__(self, session):
      
	self.session = session
        
        # Module declaration
        super(PluginManager, self).__init__("PluginManager", self.session)
       

      
    def test_plugin(self):
	LOG.info(" - test_plugin CALLED...")
	
	name = "plugin_ZERO"
	path = "./lightningrod/plugins/"+name+".py"
      
        if os.path.exists(path):
	  
            LOG.info("Plugin PATH: " + path)
                        
            task = imp.load_source("plugin", path)
            LOG.info("Plugin "+name+" imported!")
            
           
            worker = task.Worker(name, self.session)
            worker.setStatus("STARTED")
            result = worker.checkStatus()
            
            yield worker.start()
            
            returnValue(result)
            
            """
            yield task.PluginExec("plugin_ZERO", self.session)
            result = "Plugin "+name+" started!"
            LOG.info(result)
	    returnValue(result)
	    """
	  
        else: 
            LOG.warning("ERROR il file "+path+" non esiste!")

                
    def PluginInject(self):
	LOG.info(" - PluginInject CALLED...")
	yield makeNothing() 
	result = "plugin result: PluginInject!\n"
	LOG.info(result)
	returnValue(result)

    def PluginStart(self):
	LOG.info(" - PluginStart CALLED...")
	yield makeNothing() 
	result = "plugin result: PluginStart!\n"
	LOG.info(result)
	returnValue(result)
      
    def PluginStop(self):
	LOG.info(" - PluginStop CALLED...")
	yield makeNothing()
	result = "plugin result: PluginStop!\n"
	LOG.info(result)
	returnValue(result)

    def PluginCall(self):
	LOG.info(" - PluginCall CALLED...")
	yield makeNothing()
	result = "plugin result: PluginCall!\n"
	LOG.info(result)
	returnValue(result)

    def PluginRemove(self):
	LOG.info(" - PluginRemove CALLED...")
	yield makeNothing() 
	result = "plugin result: PluginRemove!\n"
	LOG.info(result)
	returnValue(result)   
      
      
      
      
      
      
      