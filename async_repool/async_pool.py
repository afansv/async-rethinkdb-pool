from asyncio import Queue, Lock

from typing import Dict, Union, Any, AsyncIterable
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

__all__ = ['AsyncConnectionPool', 'fetch_cursor', 'PoolException']

_log = logging.getLogger(__name__)


class PoolException(Exception):
    pass


async def fetch_cursor(cursor) -> AsyncIterable[Dict[str, Any]]:
    """
    Additonal method that wraps asyncio rethinkDB cursos to AsyncIterable.
    Just util method to allow async for usage
    """
    while await cursor.fetch_next():
        yield await cursor.next()


class AsyncConnectionWrapper(object):

    def __init__(self, pool: 'AsyncConnectionPool', conn=None, **kwargs) -> None:
        self._pool = pool
        self._conn = conn
        self._connection_kwargs = kwargs
        if conn is not None:
            self.connected_at = time.time()
        else:
            self.connected_at = None

    async def init_wrapper(self) -> None:
        if self._conn is None:
            self._conn = await R.connect(**self._connection_kwargs)
        self.connected_at = time.time()

    @property
    def expire(self) -> bool:
        if not self._pool.connection_ttl:
            return False
        now = time.time()
        return (now - self.connected_at) > self._pool.connection_ttl

    @property
    def connection(self):
        return self._conn


class AsyncConnectionContextManager:  # pylint: disable=too-few-public-methods

    def __init__(self, pool: 'AsyncConnectionPool') -> None:
        self.pool: 'AsyncConnectionPool' = pool
        self.conn: AsyncConnectionWrapper = None

    async def __aenter__(self) -> AsyncConnectionWrapper:
        self.conn = await self.pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            await self.pool.release(self.conn)


class AsyncConnectionPool(object):

    def __init__(
            self, rethinkdb_connection_kwargs: Dict[str, Union[str, int]],
            pool_size: int = 3, connection_ttl: int = 3600) -> None:
        self.pool_size = pool_size
        self.connection_ttl = connection_ttl
        self.connection_kwargs = rethinkdb_connection_kwargs
        self._pool: Queue = Queue()
        self._pool_lock = Lock()
        self._current_acquired = 0

    async def init_pool(self) -> None:
        for _ in range(0, self.pool_size):
            await self._pool.put(await self.new_conn())

    async def new_conn(self) -> AsyncConnectionWrapper:
        """
        Create a new AsyncConnectionWrapper instance
        """
        _log.debug("Opening new connection to rethinkdb with args=%s", self.connection_kwargs)
        connection_wrapper = AsyncConnectionWrapper(self, **self.connection_kwargs)
        await connection_wrapper.init_wrapper()
        return connection_wrapper

    async def acquire(self):
        """
        Acquire a connection
        :returns: Returns a RethinkDB connection
        :raises Empty: No resources are available before timeout.
        """
        await self._pool_lock.acquire()
        conn_wrapper = await self._pool.get()
        if conn_wrapper.expire:
            _log.debug('Recreate connection due to ttl expire')
            await conn_wrapper.connection.close()
            conn_wrapper = await self.new_conn()
        self._current_acquired += 1
        self._pool_lock.release()
        return conn_wrapper.connection

    async def release(self, conn) -> None:
        """
        Release a previously acquired connection.
        The connection is put back into the pool.
        """
        await self._pool_lock.acquire()
        await self._pool.put(AsyncConnectionWrapper(self, conn))
        self._current_acquired -= 1
        self._pool_lock.release()

    @property
    def empty(self) -> bool:
        return self._pool.empty()

    async def release_pool(self) -> None:
        """Release pool and all its connection"""
        if self._current_acquired > 0:
            raise PoolException("Can't release pool: %d connection(s) still acquired" % self._current_acquired)
        while not self._pool.empty():
            conn = await self.acquire()
            await conn.close()
        self._pool = None

    def connect(self) -> AsyncConnectionContextManager:
        '''Acquire a new connection with `with` statement and auto release the connection after
            go out the with block
        :param timeout: @see #aquire
        :returns: Returns a RethinkDB connection
        :raises Empty: No resources are available before timeout.
        '''
        return AsyncConnectionContextManager(self)
