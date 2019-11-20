try:
    import wrapt
    import urllib3
    import time, os


    from signoz import Singleton
    statsd = Singleton.getStatsd()

    REQUEST_COUNT_METRIC_NAME = "external_url_request_count"
    REQUEST_LATENCY_METRIC_NAME = 'external_url_request_latency_seconds'

    def collect(instance, args, kwargs):
        """ Build and return a fully qualified URL for this request """
        try:
            kvs = dict()
            kvs['host'] = instance.host
            kvs['port'] = instance.port or 80

            if args is not None and len(args) is 2:
                kvs['method'] = args[0]
                kvs['path'] = args[1]
            else:
                kvs['method'] = kwargs.get('method')
                kvs['path'] = kwargs.get('path')
                if kvs['path'] is None:
                    kvs['path'] = kwargs.get('url')
            
            # Strip any secrets from potential query params
            if kvs.get('path') is not None and ('?' in kvs['path']):
                parts = kvs['path'].split('?')
                kvs['path'] = parts[0]

            if type(instance) is urllib3.connectionpool.HTTPSConnectionPool:
                kvs['url'] = 'https://%s:%d%s' % (kvs['host'], kvs['port'], kvs['path'])
            else:
                kvs['url'] = 'http://%s:%d%s' % (kvs['host'], kvs['port'], kvs['path'])
        except Exception:
            print ("urllib3 collect error")
            return kvs
        else:
            return kvs

    @wrapt.patch_function_wrapper('urllib3', 'HTTPConnectionPool.urlopen')
    def urlopen_with_signoz(wrapped, instance, args, kwargs):

        print ("inside urlopen")
        kvs = collect(instance, args, kwargs)
        print("kvs collected")

        start_time = time.time()
        rv = wrapped(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000
        # print ("External URL: ", kvs['url'])
        # print ("-> Time External url: ", execution_time)

        print("Before sending metrics")
        print (kvs['port'], kvs['path'], kvs['method'])
        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'address:%s' % (kvs['host'] + ":" + str(kvs['port'])), 
                'endpoint:%s' % kvs['path'],
                'method:%s', kvs['method'],
                'status:%s', str(rv.status)
                ]
        )

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'endpoint:%s' % kvs['path'],
                    ]
        )

        return rv

    print ("Instrumenting urllib3")
except ImportError:
    pass