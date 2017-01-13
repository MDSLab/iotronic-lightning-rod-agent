# The MIT License
# 
# Copyright 2012 Nicola Peditto n.peditto@gmail.com
# Copyright 2012 Fabio Verboso fabio.verboso@gmail.com
# 
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time#, shutil

from lightningrod.plugins import Plugin


from oslo_log import log as logging
LOG = logging.getLogger(__name__)

"""
def PluginExec(name, session):
    LOG.info("Booting "+name+"...")
    #return "DONE - " + name
    Worker(name, session).start()
"""    

class Worker(Plugin.Plugin):
    
    def __init__(self, name, session):
        super(Worker, self).__init__(name, session)


    def run(self):
                        
        self.Done()
        
        

        

        
