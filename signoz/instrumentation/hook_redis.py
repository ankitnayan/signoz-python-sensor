try:
    import wrapt
    import redis
    import time

    def get_url(instance, args, kwargs):
        url = ""
        try:
            ckw = instance.connection_pool.connection_kwargs

            host = ckw.get('host', None)
            port = ckw.get('port', '6379')
            db = ckw.get('db', None)

            if host is not None:
                url = "redis://%s:%s" % (host, port)
                if db is not None:
                    url = url + "/%s" % db
                
        except:
            print ("redis.collect_tags non-fatal error")
        
        return url


    def execute_command_with_signoz(wrapped, instance, args, kwargs):


        url =  get_url(instance, args, kwargs)
        command = args[0]
        print ("Redis url: ", url)
        print ("Redis command: ", command)

        start_time = time.time()
        rv = wrapped(*args, **kwargs)

        print ("-> Time Redis: ", time.time() - start_time)

        return rv


    def execute_pipeline_with_signoz(wrapped, instance, args, kwargs):

        try:
            url = get_url(instance, args, kwargs)
            command = 'PIPELINE'
            pipe_cmds = []
            for e in instance.command_stack:
                pipe_cmds.append(e[0][0])
            
            print ("Redis url: ", url)
            print ("Redis Pipeline Commands: ", pipe_cmds)

        except Exception as e:
            # If anything breaks during K/V collection, just log a debug message
            print ("Error collecting pipeline commands")


        start_time = time.time()
        rv = wrapped(*args, **kwargs)
        print ("-> Time Redis Pipeline: ", time.time() - start_time)

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