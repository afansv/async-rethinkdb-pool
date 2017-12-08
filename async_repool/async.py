from queue import Queue
from typing import Dict, Union, Optional
from threading import Lock, Thread, Event
import time
import logging

import rethinkdb as R

__author__ = "Bogdan Gladyshev"
__copyright__ = "Copyright 2017, Bogdan Gladyshev"
__credits__ = ["Bogdan Gladyshev"]
__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Bogdan Gladyshev"
__email__ = "siredvin.dark@gmail.com"
__status__ = "Production"

_log = logging.getLogger(__name__)


class PoolException(Exception):
    pass


class AsyncConnectionWrapper(object):

    def __init__(self, pool: 'AsyncConnectionPool', conn=None, **kwargs) -> None:
        self._pool = pool
        if conn is None:
            self._conn = R.connect(**kwargs)
        else:
            self._conn = conn
        self.connected_at = time.time()

    @property
    def connection(self):
        return self._conn


class AsyncConnectionContextManager:

    def __init__(self, pool: 'AsyncConnectionPool', timeout: Optional[int] = None) -> None:
        self.pool: 'AsyncConnectionPool' = pool
        self.timeout: Optional[int] = timeout
        self.conn: AsyncConnectionWrapper = None

    def __enter__(self) -> AsyncConnectionWrapper:
        self.conn = self.pool.acquire(self.timeout)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            self.pool.release(self.conn)


class AsyncConnectionPoolCleanupThread(Thread):

    def __init__(self, stop_event: Event, cleanup_timeout: int, pool: 'AsyncConnectionPool') -> None:
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.cleanup_timeout = cleanup_timeout
        self.pool = pool

    def run(self) -> None:
        _log.debug("Starting cleanup thread")
        while not self.stop_event.is_set():
            self.stop_event.wait(self.cleanup_timeout)
            self.pool.cleanup()
        _log.debug("Cleanup thread ending")

class AsyncConnectionPool(object):

    def __init__(
            self, rethinkdb_connection_kwargs: Dict[str, Union[str, int]],
            pool_size: int = 10, connection_ttl: int = 3600,
            cleanup_timeout: int = 60) -> None:
        self.pool_size = pool_size
        self.connection_ttl = connection_ttl
        self.connection_kwargs = rethinkdb_connection_kwargs
        self.cleanup_timeout = cleanup_timeout
        self._pool = Queue()
        self._pool_lock = Lock()
        self._pool_lock.acquire()
        for _ in range(0, self.pool_size):
            self._pool.put(self.new_conn())
        self._current_acquired = 0
        self._pool_lock.release()

        if self.cleanup_timeout > 0:
            self._cleanup_stop_event = Event()
            self._cleanup_thread = AsyncConnectionPoolCleanupThread(
                self._cleanup_stop_event,
                self.cleanup_timeout,
                self
            )
            self._cleanup_thread.start()
        else:
            self._cleanup_thread = None

    def new_conn(self) -> AsyncConnectionWrapper:
        """
        Create a new AsyncConnectionWrapper instance
        """
        _log.debug("Opening new connection to rethinkdb with args=%s", self.connection_kwargs)
        return AsyncConnectionPool(self._pool, **self.connection_kwargs)

    def acquire(self, timeout: Optional[int] = None):
        """Acquire a connection
        :param timeout: If provided, seconds to wait for a connection before raising
            Queue.Empty. If not provided, blocks indefinitely.
        :returns: Returns a RethinkDB connection
        :raises Empty: No resources are available before timeout.
        """
        self._pool_lock.acquire()
        if timeout is None:
            conn_wrapper = self._pool.get_nowait()
        else:
            conn_wrapper = self._pool.get(True, timeout)
        self._current_acquired += 1
        self._pool_lock.release()
        return conn_wrapper.connection

    def release(self, conn) -> None:
        """Release a previously acquired connection.
        The connection is put back into the pool."""
        self._pool_lock.acquire()
        self._pool.put(AsyncConnectionWrapper(self._pool, conn))
        self._current_acquired -= 1
        self._pool_lock.release()

    def empty(self) -> bool:
        return self._pool.empty()

    def release_pool(self) -> None:
        """Release pool and all its connection"""
        if self._current_acquired > 0:
            raise PoolException("Can't release pool: %d connection(s) still acquired" % self._current_acquired)
        while not self._pool.empty():
            conn = self.acquire()
            conn.close()
        if self._cleanup_thread is not None:
            self._cleanup_stop_event.set()
            self._cleanup_thread.join()
        self._pool = None

    def cleanup(self) -> None:
        _log.debug("Cleanup function running...")
        now = time.time()
        queue_tmp = Queue()
        try:
            self._pool_lock.acquire()
            cleaned_connections_count = 0
            while not self._pool.empty():
                conn_wrapper = self._pool.get_nowait()
                if (now - conn_wrapper.connected_at) > self.connection_ttl:
                    conn_wrapper.connection.close()
                    del conn_wrapper
                    queue_tmp.put(self.new_conn())
                    cleaned_connections_count += 1
                else:
                    queue_tmp.put(conn_wrapper)
            self._pool = queue_tmp
            self._pool_lock.release()
            _log.debug("%d connection(s) cleaned", cleaned_connections_count)
        except Exception as e:
            _log.exception(e)

    def connect(self, timeout: Optional[int] = None) -> AsyncConnectionContextManager:
        '''Acquire a new connection with `with` statement and auto release the connection after
            go out the with block
        :param timeout: @see #aquire
        :returns: Returns a RethinkDB connection
        :raises Empty: No resources are available before timeout.
        '''
        return AsyncConnectionContextManager(self, timeout)
