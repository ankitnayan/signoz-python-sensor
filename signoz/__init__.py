from __future__ import absolute_import

def load(module):
    print("hello world!")

def boot_agent():
    print ("Inside boot agent")
    from .instrumentation.django import middleware
    print ("Django middleware imported")

    
boot_agent()