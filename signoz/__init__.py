from __future__ import absolute_import
import os, sys
from datadog import DogStatsd

class Singleton:

   __statsd = None

   @staticmethod 
   def getStatsd():
      """ Static access method. """
      if Singleton.__statsd == None:
         Singleton()
      return Singleton.__statsd

   def __init__(self):
      """ Virtually private constructor. """
      if Singleton.__statsd != None:
         raise Exception("This class is a singleton!")
      else:
         Singleton.__statsd = DogStatsd(host=os.environ['NODE_IP'], port=9125)



def load(module):
    print("Inside Load Module!")

def boot_agent():
   # print ("Inside Boot Agent!")
   Singleton()

   from .instrumentation import django
   from .instrumentation import flask
   from .instrumentation import hook_mysqlclient
   from .instrumentation import hook_mysqlpython
   from .instrumentation import hook_redis
   from .instrumentation import hook_sqlalchemy
   from .instrumentation import hook_urllib3

   try:
      from .instrumentation import hook_pymongo
   except ImportError:
      pass
   

    
boot_agent()