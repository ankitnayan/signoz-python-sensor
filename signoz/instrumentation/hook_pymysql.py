try:
    import pymysql
    from .pep0249 import ConnectionFactory

    cf = ConnectionFactory(connect_func=pymysql.connect, module_name='mysql')

    setattr(pymysql, 'connect', cf)
    if hasattr(pymysql, 'Connect'):
        setattr(pymysql, 'Connect', cf)

    # print ("Instrumenting pymysql")
except ImportError:
    pass