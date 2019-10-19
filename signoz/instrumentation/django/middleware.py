from __future__ import absolute_import

import sys
import wrapt


DJ_SIGNOZ_MIDDLEWARE = 'signoz.instrumentation.django.middleware.SignozMiddleware'

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


class SignozMiddleware(MiddlewareMixin):
    """ Django Middleware to provide Application Metrics for Signoz """
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request):
        print ("Processing Request")


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
