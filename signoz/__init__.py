from __future__ import absolute_import

def load(module):
    print("Inside Load Module!")

def boot_agent():
    print ("Inside Boot Agent!")

    from .instrumentation.django import middleware
    from .instrumentation import flask


    
boot_agent()