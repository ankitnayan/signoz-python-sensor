try:
    import wrapt
    import redis
    import time
    import os

    from signoz import Singleton
    statsd = Singleton.getStatsd()

    REQUEST_COUNT_METRIC_NAME = "redis_request_count"
    REQUEST_LATENCY_METRIC_NAME = 'redis_request_latency_seconds'


    def get_address_n_db(instance, args, kwargs):
        address = ""
        try:
            ckw = instance.connection_pool.connection_kwargs

            host = ckw.get('host', None)
            port = ckw.get('port', '6379')
            db = ckw.get('db', None)

            if host is not None:
                address = "redis://%s:%s" % (host, port)
                # if db is not None:
                #     url = url + "/%s" % db
                
        except:
            print ("redis.collect_tags non-fatal error")
        
        return (address, db)


    def execute_command_with_signoz(wrapped, instance, args, kwargs):

        (address, db) =  get_address_n_db(instance, args, kwargs)
        command = args[0]
        # print ("Redis address: ", address)
        # print ("Redis command: ", command)

        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'command:%s' % command, 
                'db:%s' % db, 
                'address:%s' % address, 
                ]
        )

        start_time = time.time()
        rv = wrapped(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000
        # print ("-> Time Redis: ", execution_time)
        
        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'command:%s' % command,
                    'db:%s' % db, 
                    'address:%s' % address,
                    ]
        )

        return rv


    def execute_pipeline_with_signoz(wrapped, instance, args, kwargs):

        command = 'PIPELINE'
        (address, db) = get_address_n_db(instance, args, kwargs)
        
        try:
            
            pipe_cmds = []
            for e in instance.command_stack:
                pipe_cmds.append(e[0][0])
            
            # print ("Redis address: ", address)
            # print ("Redis Pipeline Commands: ", pipe_cmds)

            statsd.increment(REQUEST_COUNT_METRIC_NAME,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                    # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                    'command:%s' % command, 
                    'db:%s' % str(db), 
                    'address:%s' % address, 
                    ]
            )

        except Exception as e:
            # If anything breaks during K/V collection, just log a debug message
            print ("Error collecting pipeline commands")


        start_time = time.time()
        rv = wrapped(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000
        # print ("-> Time Redis Pipeline: ", execution_time)

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'command:%s' % command,
                    'db:%s' % str(db), 
                    'address:%s' % address,
                    ]
        )


        return rv

    if redis.VERSION < (3,0,0):
        wrapt.wrap_function_wrapper('redis.client', 'BasePipeline.execute', execute_pipeline_with_signoz)
        wrapt.wrap_function_wrapper('redis.client', 'StrictRedis.execute_command', execute_command_with_signoz)
    else:
        wrapt.wrap_function_wrapper('redis.client', 'Pipeline.execute', execute_pipeline_with_signoz)
        wrapt.wrap_function_wrapper('redis.client', 'Redis.execute_command', execute_command_with_signoz)

        print ("Instrumenting redis")
except ImportError:
    pass