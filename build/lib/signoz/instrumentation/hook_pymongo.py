from wrapt import ObjectProxy
import pymongo
import six, time, os


from signoz import Singleton
statsd = Singleton.getStatsd()

_MongoClient = pymongo.MongoClient


MONGO_ADDRESS = getattr(_MongoClient, 'HOST') + ":" + str(getattr(_MongoClient, 'PORT'))

REQUEST_COUNT_METRIC_NAME = "mongo_request_count"
REQUEST_LATENCY_METRIC_NAME = 'mongo_request_latency_seconds'

class Command(object):
    """ Command stores information about a pymongo network command, """

    __slots__ = ['name', 'coll', 'db', 'tags', 'metrics', 'query']

    def __init__(self, name, db, coll):
        self.name = name
        self.coll = coll
        self.db = db
        self.tags = {}
        self.metrics = {}
        self.query = None

    def __repr__(self):
        return (
            'Command('
            'name=%s,'
            'db=%s,'
            'coll=%s)'
        ) % (self.name, self.db, self.coll)

def parse_query(query):
    """ Return a command parsed from the given mongo db query. """
    db, coll = None, None
    ns = getattr(query, 'ns', None)
    if ns:
        # version < 3.1 stores the full namespace
        db, coll = _split_namespace(ns)
    else:
        # version >= 3.1 stores the db and coll seperately
        coll = getattr(query, 'coll', None)
        db = getattr(query, 'db', None)

    # pymongo < 3.1 _Query does not have a name field, so default to 'query'
    cmd = Command(getattr(query, 'name', 'query'), db, coll)
    cmd.query = query.spec
    return cmd



# DEV: There is `six.u()` which does something similar, but doesn't have the guard around `hasattr(s, 'decode')`
def to_unicode(s):
    """ Return a unicode string for the given bytes or string instance. """
    # No reason to decode if we already have the unicode compatible object we expect
    # DEV: `six.text_type` will be a `str` for python 3 and `unicode` for python 2
    # DEV: Double decoding a `unicode` can cause a `UnicodeEncodeError`
    #   e.g. `'\xc3\xbf'.decode('utf-8').decode('utf-8')`
    if isinstance(s, six.text_type):
        return s

    # If the object has a `decode` method, then decode into `utf-8`
    #   e.g. Python 2 `str`, Python 2/3 `bytearray`, etc
    if hasattr(s, 'decode'):
        return s.decode('utf-8')

    # Always try to coerce the object into the `six.text_type` object we expect
    #   e.g. `to_unicode(1)`, `to_unicode(dict(key='value'))`
    return six.text_type(s)

def _split_namespace(ns):
    """ Return a tuple of (db, collecton) from the 'db.coll' string. """
    if ns:
        # NOTE[matt] ns is unicode or bytes depending on the client version
        # so force cast to unicode
        split = to_unicode(ns).split('.', 1)
        if len(split) == 1:
            raise Exception("namespace doesn't contain period: %s" % ns)
        return split
    return (None, None)

class TracedMongoClient(ObjectProxy):

    def __init__(self, client=None, *args, **kwargs):
        # To support the former trace_mongo_client interface, we have to keep this old interface
        # TODO(Benjamin): drop it in a later version
        if not isinstance(client, _MongoClient):
            # Patched interface, instantiate the client

            # client is just the first arg which could be the host if it is
            # None, then it could be that the caller:

            # if client is None then __init__ was:
            #   1) invoked with host=None
            #   2) not given a first argument (client defaults to None)
            # we cannot tell which case it is, but it should not matter since
            # the default value for host is None, in either case we can simply
            # not provide it as an argument
            if client is None:
                client = _MongoClient(*args, **kwargs)
            # else client is a value for host so just pass it along
            else:
                client = _MongoClient(client, *args, **kwargs)

        super(TracedMongoClient, self).__init__(client)
        # NOTE[matt] the TracedMongoClient attempts to trace all of the network
        # calls in the trace library. This is good because it measures the
        # actual network time. It's bad because it uses a private API which
        # could change. We'll see how this goes.
        client._topology = TracedTopology(client._topology)



class TracedTopology(ObjectProxy):

    def __init__(self, topology):
        super(TracedTopology, self).__init__(topology)

    def select_server(self, *args, **kwargs):
        s = self.__wrapped__.select_server(*args, **kwargs)
        if not isinstance(s, TracedServer):
            s = TracedServer(s)

        return s

class TracedServer(ObjectProxy):

    def __init__(self, server):
        super(TracedServer, self).__init__(server)

    def _signoz_trace_operation(self, operation):
        cmd = None
        # Only try to parse something we think is a query.
        if self._is_query(operation):
            try:
                cmd = parse_query(operation)
            except Exception:
                print ('error parsing query')

        # print ("DB: ", cmd.db)
        # print ("Collection: ", cmd.coll)
        # print ("Tags: ", cmd.tags)

        return (cmd.db, cmd.coll, cmd.tags)



    # Pymongo >= 3.9
    def run_operation_with_response(self, sock_info, operation, *args, **kwargs):


        (db, collection, tags) = self._signoz_trace_operation(operation)

        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'command:%s' % getattr(operation, 'name'), 
                'db:%s' % db, 
                'collection:%s' % collection,
                'address:%s' % MONGO_ADDRESS, 
                ]
        )

        start_time = time.time()
        result = self.__wrapped__.run_operation_with_response(
                sock_info,
                operation,
                *args,
                **kwargs
            )
        execution_time = (time.time() - start_time) * 1000

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'command:%s' % getattr(operation, 'name'),
                    'address:%s' % MONGO_ADDRESS,
                    ]
        )
        # print ("-> Mongo (Time Taken): ", execution_time)
        # print ("Pymongo - Response: ", result)
        # print ("Pymongo - Response Address: ", result.address)
        
        return result



    # Pymongo < 3.9
    
    def send_message_with_response(self, operation, *args, **kwargs):
        
        (db, collection, tags) = self._signoz_trace_operation(operation)

        statsd.increment(REQUEST_COUNT_METRIC_NAME,
            tags=[
                'app_name:%s' % os.environ['APP_NAME'],
                'kubernetes_namespace:%s' % os.environ['POD_NAMESPACE'],
                'kubernetes_pod_name:%s' % os.environ['POD_NAME'],
                'command:%s' % getattr(operation, 'name'), 
                'db:%s' % db, 
                'collection:%s' % collection,
                'address:%s' % MONGO_ADDRESS, 
                ]
        )

        start_time = time.time()

        result = self.__wrapped__.send_message_with_response(
                operation,
                *args,
                **kwargs
            )

        execution_time = (time.time() - start_time)*1000

        statsd.histogram(REQUEST_LATENCY_METRIC_NAME,
                execution_time,
                tags=[
                    'app_name:%s' % os.environ['APP_NAME'],
                    'command:%s' % getattr(operation, 'name'),
                    'address:%s' % MONGO_ADDRESS,
                    ]
        )

        # print ("Pymongo - Response: ", result)
        # print ("Pymongo - Response Address: ", result.address)

        return result


    @staticmethod
    def _is_query(op):
        # NOTE: _Query should alwyas have a spec field
        return hasattr(op, 'spec')


setattr(pymongo, 'MongoClient', TracedMongoClient)
