from __future__ import absolute_import

def load(module):
    print("Inside Load Module!")

def boot_agent():
    print ("Inside Boot Agent!")

    try:
        from .instrumentation.django import middleware
    except:
        pass

    from .instrumentation import flask

    
boot_agent()