try:
    import sqlalchemy
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import re, time, os

    from signoz import Singleton
    statsd = Singleton.getStatsd()


    REQUEST_COUNT_METRIC_NAME = "sqlalchemy_request_count"
    REQUEST_LATENCY_METRIC_NAME = 'sqlalchemy_request_latency_seconds'

    # Used by sql_sanitizer
    regexp_sql_values = re.compile('(\'[\s\S][^\']*\'|\d*\.\d+|\d+|NULL)')


    def sql_sanitizer(sql):
        """
        Removes values from valid SQL statements and returns a stripped version.
        :param sql: The SQL statement to be sanitized
        :return: String - A sanitized SQL statement without values.
        """
        return regexp_sql_values.sub('?', sql)



    url_regexp = re.compile('\/\/(\S+@)')
    start_time = None
    url = ""
    query = ""

    @event.listens_for(Engine, 'before_cursor_execute', named=True)
    def receive_before_cursor_execute(**kw):

        global start_time
        start_time = time.time()
        # context = kw['context']

    @event.listens_for(Engine, 'after_cursor_execute', named=True)
    def receive_after_cursor_execute(**kw):
        # print ("SqlAlchemy - after_cursor_execute")
        execution_time = (time.time() - start_time) * 1000
        # print ("-> Time taken: ", execution_time)

        conn = kw['conn']

        global url
        url = url_regexp.sub('//', str(conn.engine.url))

        global query
        query = sql_sanitizer(kw['statement'])
        # print ('sqlalchemy.sql', query)
        # print ('sqlalchemy.eng', conn.engine.name)
        # print ('sqlalchemy.url', url_regexp.sub('//', url))


        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'query:%s' % query, 
                'address:%s' % url, 
                'is_exception:%s' % str(0)
                ]
        )

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
            execution_time,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'query:%s' % query,
                'address:%s' % url, 
                'is_exception:%s' % str(0)
                ]
        )

    @event.listens_for(Engine, 'dbapi_error', named=True)
    def receive_dbapi_error(**kw):
        # context = kw['context']

        # print ("-> Time taken (Exception): ", time.time() - start_time)

        execution_time = (time.time() - start_time) * 1000

        conn = kw['conn']

        global url
        url = url_regexp.sub('//', str(conn.engine.url))

        global query
        query = sql_sanitizer(kw['statement'])
        # print ('sqlalchemy.sql', query)
        # print ('sqlalchemy.eng', conn.engine.name)
        # print ('sqlalchemy.url', url_regexp.sub('//', url))


        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'query:%s' % query, 
                'address:%s' % url, 
                'is_exception:%s' % str(1)
                ]
        )

        if 'exception' in kw:
            e = kw['exception']

            statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'query:%s' % query,
                    'address:%s' % url, 
                    'is_exception:%s' % str(1)
                    ]
            )
            # print ("***** -> Error SqlAlchemy: ", str(e))

    print ("Instrumenting sqlalchemy")
except ImportError:
    pass