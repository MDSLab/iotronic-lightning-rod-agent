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
import stevedore, sys
from six import moves
from stevedore import extension
import inspect
from lightningrod.config import mod_queue

from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn.twisted.util import sleep

"""
def load_single_module(new_module):
  
    modules = named.NamedExtensionManager(
	namespace='s4t.modules',
	names=[new_module],
	invoke_on_load=True,
	#invoke_args=(self,),
    )
"""
  


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
        
        super(Utility, self).__init__()
        
	self.name = "Utility"
	self.session = session
        print "Starting module " + self.name + "..."
	
	
	    
    def hello(self, client_name, message):
	import random
	s = random.uniform(0.5, 3.0)
	yield sleep(s)
	result = "Hello by board to Conductor "+client_name+" that said me "+message+" - Time: "+'%.2f' %s
	#result = yield "Hello by board to Conductor "+client_name+" that said me "+message
	print "DEVICE hello result: "+str(result)
	    
	returnValue(result)
      
      
      
    def add(self, x, y):
	c = yield x+y
	print "DEVICE add result: "+str(c)
	returnValue(c)



    def plug_and_play(self, new_module, new_class):

        print "LR modules loaded:\n\t"+new_module
        
        # Updating entry_points
        with open('/usr/local/lib/python2.7/dist-packages/Lightning_rod-0.1-py2.7.egg/EGG-INFO/entry_points.txt', 'a') as entry_points:
	  entry_points.write(new_module+'= lightningrod.modules.'+new_module+':'+new_class)
	  
	  # Reload entry_points
	  refresh_stevedore('s4t.modules')
	  print "New entry_points loaded!"
	  

	# Reading updated entry_points
	import pkg_resources
	named_objects = {}
	for ep in pkg_resources.iter_entry_points(group='s4t.modules'):
	  named_objects.update({ep.name: ep.load()})
	
	
	
	
	
	"""  
	# Reload modules  
	modules = extension.ExtensionManager(
		namespace='s4t.modules',
		#invoke_on_load=True,
		#invoke_args=(session,),
	)
		
	# Starting the new module 	
	for ext in modules.extensions:  

	  if ext.name == new_module:
	    
	    mod = ext.plugin(self.session)
	  
	    meth_list = inspect.getmembers(mod, predicate=inspect.ismethod)
	  
	    for meth in meth_list[1:]:
	      print "Wamp enabling new RPC: " + str(meth)
	      
	      #global config.mod_queue
	      #mod_queue.put(meth)
	      
	"""
	yield named_objects
	
	
	#mod_queue.put(new_module)
	
	self.session.disconnect()
	
	
	returnValue(str(named_objects))
      
	
	  
	"""
	modules = named.NamedExtensionManager(
	    namespace='s4t.modules',
	    names=[new_module],
	    invoke_on_load=True,
	    #invoke_args=(self,),
	)
	
	names = modules.__dict__

	print names
	yield str(names)
	
	returnValue(str(names))
	"""
		


