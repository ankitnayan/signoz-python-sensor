from __future__ import absolute_import

import sys, os
import wrapt
import django
import time
from datadog import DogStatsd


DJ_SIGNOZ_MIDDLEWARE = 'signoz.instrumentation.django.middleware.SignozMiddleware'

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

statsd = DogStatsd(host=os.environ['NODE_IP'], port=9125)

REQUEST_LATENCY_METRIC_NAME = 'django_request_latency_seconds'
REQUEST_COUNT_METRIC_NAME = 'django_request_count'

class SignozMiddleware(MiddlewareMixin):
    """ Django Middleware to provide Application Metrics for Signoz """
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        print ("Processing Request")
        request.start_time = time.time()

    def process_response(self, request, response):
        
        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'service:django_sample_project', 
                'method:%s' % request.method, 
                'endpoint:%s' % request.path,
                'status:%s' % str(response.status_code)
                ]
        )

        resp_time = (time.time() - request.start_time)*1000

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                resp_time,
                tags=[
                    'service:django_sample_project',
                    'endpoint:%s' % request.path,
                    ]
        )
        return response


def load_middleware_wrapper(wrapped, instance, args, kwargs):

    from django.conf import settings

    # Django >=1.10 to <2.0 support old-style MIDDLEWARE_CLASSES so we
    # do as well here
    if hasattr(settings, 'MIDDLEWARE') and settings.MIDDLEWARE is not None:
        if DJ_SIGNOZ_MIDDLEWARE in settings.MIDDLEWARE:
            return wrapped(*args, **kwargs)

        if type(settings.MIDDLEWARE) is tuple:
            settings.MIDDLEWARE = (DJ_SIGNOZ_MIDDLEWARE,) + settings.MIDDLEWARE
        elif type(settings.MIDDLEWARE) is list:
            settings.MIDDLEWARE = [DJ_SIGNOZ_MIDDLEWARE] + settings.MIDDLEWARE
        else:
            print ("Signoz: Couldn't add SignozMiddleware to Django")

    else:
        print ("Signoz: Couldn't find middleware settings")
    
    return wrapped(*args, **kwargs)


if 'django' in sys.modules:
    print ("Instrumenting django")
    wrapt.wrap_function_wrapper('django.core.handlers.base', 'BaseHandler.load_middleware', load_middleware_wrapper)

    # if 'INSTANA_MAGIC' in os.environ:
    #     # If we are instrumenting via AutoTrace (in an already running process), then the
    #     # WSGI middleware has to be live reloaded.
    #     from django.core.servers.basehttp import get_internal_wsgi_application
    #     wsgiapp = get_internal_wsgi_application()
    #     wsgiapp.load_middleware()
