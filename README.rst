=================================
AsyncIO RethinkDB connection pool
=================================


.. image:: https://img.shields.io/pypi/v/async-repool.svg
        :target: https://pypi.python.org/pypi/async-repool
.. image:: https://img.shields.io/pypi/l/async-repool.svg
        :target: https://pypi.python.org/pypi/async-repool
.. image:: https://gitlab.com/AnjiProject/async-repool/badges/master/build.svg
        :target: https://gitlab.com/AnjiProject/async-repool

:code:`async-repool` is a Python library which provides a asyncio-based connection pool management for accessing a RethinkDB database. :code:`async-repool` creates and maintains a configurable pool of active connection to a RethinkDB database. These connections are then available individually through a basic API.

Internally, repool uses the Python `AsyncIO Queue`_ class which is not thread-safe. This means that the same connection pool cannot be share between several threads, please, use asyncio with process workers instead.

This is just asyncio-based clone of repool_.

Installation
------------

:code:`async-repool` is available as a python library on Pypi. Installation is very simple using pip :

.. code:: bash

    $ pip install async_repool

This will install :code:`async-repool` as well as rethinkdb dependency.

Basic usage
-----------

A new connection pool using default connection configurations can simply be created by:

.. code:: python

    from async_repool import AsyncConnectionPool

    pool = AsyncConnectionPool(dict())  # Required argument is kwargs for R.connect function
    await pool.init_pool()
    conn = await pool.acquire()         #returns a Connection instance
    await r.table('heroes').run(conn)   #do RethinkDB stuff
    # ...
    pool.release(conn)          #put back connection to the pool
    await pool.release_pool()         #release pool (close rethinkdb connections)

    # ...
    async with pool.connect() as conn1:
        # do something with conn1
    # pool.release(conn1) is automatically called after leaving the with code block


Optional arguments
------------------

:code:`AsyncConnectionPool` creation accepts a number of optional arguments:

- :code:`pool_size`: set the pool size, ie. the number of connections opened simultaneously (default=3).
- :code:`connection_ttl`: set the connection time to live. Connections older than TTL are automatically closed and re-opened when acquire (default=3600 seconds, set to 0 for disable)

.. _`AsyncIO Queue`: https://docs.python.org/3/library/asyncio-queue.html
.. _repool: https://github.com/njouanin/repool