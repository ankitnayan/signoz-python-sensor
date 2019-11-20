try:
    import MySQLdb
    from pep0249 import ConnectionFactory
    cf = ConnectionFactory(connect_func=MySQLdb.connect, module_name='mysql')

    setattr(MySQLdb, 'connect', cf)
    if hasattr(MySQLdb, 'Connect'):
        setattr(MySQLdb, 'Connect', cf)
        
    print ("Instrumenting mysql-python")
except ImportError:
    pass