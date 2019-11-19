try:
    import wrapt
    import urllib3
    import time

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
    def urlopen_with_instana(wrapped, instance, args, kwargs):

        kvs = collect(instance, args, kwargs)

        start_time = time.time()
        rv = wrapped(*args, **kwargs)
        print ("External URL: ", kvs['url'])
        print ("-> Time External url: ", time.time() - start_time)
        return rv

    print ("Instrumenting urllib3")
except ImportError:
    pass