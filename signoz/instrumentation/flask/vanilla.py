import os
import wrapt
from flask import request
import time

from signoz import Singleton
statsd = Singleton.getStatsd()

REQUEST_LATENCY_METRIC_NAME = 'flask_request_latency_seconds'
REQUEST_COUNT_METRIC_NAME = 'flask_request_count'


def before_request_with_signoz(*argv, **kwargs):
    request.start_time = time.time()


def after_request_with_signoz(response):

    statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'service:flask-test-project',
                'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'method:%s' % request.method, 
                'endpoint:%s' % request.path,
                'status:%s' % str(response.status_code)
                ]
    )

    resp_time = (time.time() - request.start_time)*1000

    statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
            resp_time,
            tags=[
                'service:flask-test-project',
                'endpoint:%s' % request.path,
                ]
    )

    return response


def teardown_request_with_signoz(*argv, **kwargs):

    return None


@wrapt.patch_function_wrapper('flask', 'Flask.full_dispatch_request')
def full_dispatch_request_with_instana(wrapped, instance, argv, kwargs):

    instance.after_request(after_request_with_signoz)
    instance.before_request(before_request_with_signoz)
    instance.teardown_request(teardown_request_with_signoz)

    return wrapped(*argv, **kwargs)
