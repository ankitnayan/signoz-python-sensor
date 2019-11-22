import os
import wrapt
from flask import request, request_started, request_finished, got_request_exception
import time

from signoz.instrumentation.utils import split_endpoint

from signoz import Singleton
statsd = Singleton.getStatsd()



REQUEST_LATENCY_METRIC_NAME = 'signoz_application_request_latency_seconds'
REQUEST_COUNT_METRIC_NAME = 'signoz_application_request_count'


def request_started_with_signoz(sender, **extra):
    request.start_time = time.time()


def request_finished_with_signoz(sender, response, **extra):

    statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'method:%s' % request.method, 
                'endpoint:%s' % split_endpoint(request.path),
                'status:%s' % str(response.status_code)
                ]
    )

    resp_time = (time.time() - request.start_time)*1000

    statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
            resp_time,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'endpoint:%s' % split_endpoint(request.path),
                ]
    )

    return response

def log_exception_with_signoz(sender, exception, **extra):

    return None

def teardown_request_with_signoz(*argv, **kwargs):

    return None


@wrapt.patch_function_wrapper('flask', 'Flask.full_dispatch_request')
def full_dispatch_request_with_instana(wrapped, instance, argv, kwargs):

    got_request_exception.connect(log_exception_with_signoz, instance)
    request_started.connect(request_started_with_signoz, instance)
    request_finished.connect(request_finished_with_signoz, instance)
    instance.teardown_request(teardown_request_with_signoz)

    return wrapped(*argv, **kwargs)
