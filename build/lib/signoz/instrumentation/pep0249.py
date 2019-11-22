# This is a wrapper for PEP-0249: Python Database API Specification v2.0

import wrapt
import re
import time, os

from signoz import Singleton
statsd = Singleton.getStatsd()


REQUEST_COUNT_METRIC_NAME = "mysql_request_count"
REQUEST_LATENCY_METRIC_NAME = 'mysql_request_latency_seconds'


# Used by sql_sanitizer
regexp_sql_values = re.compile('(\'[\s\S][^\']*\'|\d*\.\d+|\d+|NULL)')


def sql_sanitizer(sql):
    """
    Removes values from valid SQL statements and returns a stripped version.
    :param sql: The SQL statement to be sanitized
    :return: String - A sanitized SQL statement without values.
    """
    return regexp_sql_values.sub('?', sql)



class CursorWrapper(wrapt.ObjectProxy):
    __slots__ = ('_module_name', '_connect_params', '_cursor_params')

    def __init__(self, cursor, module_name,
                 connect_params=None, cursor_params=None):
        super(CursorWrapper, self).__init__(wrapped=cursor)
        self._module_name = module_name
        self._connect_params = connect_params
        self._cursor_params = cursor_params
        # print ("Instrumenting mysql cursor")



    def execute(self, sql, params=None):
        
        # print ("Executing mysql query -> ", sql_sanitizer(sql))
        # query = sql_sanitizer(sql)
        query = "SELECT"
        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'query:%s' % query, 

                ]
        )

        start_time = time.time()
        result = self.__wrapped__.execute(sql, params)
        execution_time = (time.time() - start_time) * 1000
        # print ("Time taken: ", execution_time)

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'query:%s' % query,
                    ]
        )
        
        return result

    def executemany(self, sql, seq_of_parameters):

        query = 'EXECUTE_MANY'
        # print ("Executing mysql many ...")
        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'query:%s' % query, 

                ]
        )
        start_time = time.time()
        result = self.__wrapped__.executemany(sql, seq_of_parameters)
        execution_time = (time.time() - start_time) * 1000

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'query:%s' % query,
                    ]
        )
        return result

    def callproc(self, proc_name, params):
        
        # print ("Calling mysql Proc")
        query = 'PROCEDURE'
        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                # 'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                # 'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'query:%s' % query, 

                ]
        )

        start_time = time.time()
        result = self.__wrapped__.callproc(proc_name, params)
        execution_time = (time.time() - start_time) * 1000

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'command:%s' % query,
                    ]
        )

        # print ("CallProc mysql Result: ", result)
        return result

class ConnectionWrapper(wrapt.ObjectProxy):
    __slots__ = ('_module_name', '_connect_params')

    def __init__(self, connection, module_name, connect_params):
        super(ConnectionWrapper, self).__init__(wrapped=connection)
        self._module_name = module_name
        self._connect_params = connect_params


    def cursor(self, *args, **kwargs):
        return CursorWrapper(
            cursor=self.__wrapped__.cursor(*args, **kwargs),
            module_name=self._module_name,
            connect_params=self._connect_params,
            cursor_params=(args, kwargs) if args or kwargs else None)

    def begin(self):
        return self.__wrapped__.begin()

    def commit(self):
        return self.__wrapped__.commit()

    def rollback(self):
        return self.__wrapped__.rollback()


class ConnectionFactory(object):
    def __init__(self, connect_func, module_name):
        self._connect_func = connect_func
        self._module_name = module_name
        self._wrapper_ctor = ConnectionWrapper

    def __call__(self, *args, **kwargs):
        connect_params = (args, kwargs) if args or kwargs else None

        return self._wrapper_ctor(
            connection=self._connect_func(*args, **kwargs),
            module_name=self._module_name,
            connect_params=connect_params)