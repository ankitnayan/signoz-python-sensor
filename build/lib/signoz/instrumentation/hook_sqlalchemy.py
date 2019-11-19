try:
    import sqlalchemy
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import re, time

    url_regexp = re.compile('\/\/(\S+@)')
    start_time = None

    @event.listens_for(Engine, 'before_cursor_execute', named=True)
    def receive_before_cursor_execute(**kw):

            context = kw['context']
            conn = kw['conn']
            url = str(conn.engine.url)
            print ('sqlalchemy.sql', kw['statement'])
            print ('sqlalchemy.eng', conn.engine.name)
            print ('sqlalchemy.url', url_regexp.sub('//', url))
            global start_time
            start_time = time.time()


    @event.listens_for(Engine, 'after_cursor_execute', named=True)
    def receive_after_cursor_execute(**kw):
        print ("SqlAlchemy - after_cursor_execute")
        print ("-> Time taken: ", time.time() - start_time)

    @event.listens_for(Engine, 'dbapi_error', named=True)
    def receive_dbapi_error(**kw):
        context = kw['context']

        print ("-> Time taken (Exception): ", time.time() - start_time)

        if 'exception' in kw:
            e = kw['exception']
            print ("***** -> Error SqlAlchemy: ", str(e))

                    

    print ("Instrumenting sqlalchemy")
except ImportError:
    pass