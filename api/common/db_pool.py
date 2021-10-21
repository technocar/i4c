import asyncpg
from common import dbcfg


class DatabaseConnection:
    db_pool = None
    __slots__ = ['pconn', 'conn']

    def __init__(self, pconn):
        self.pconn = pconn
        self.conn = None

    async def __aenter__(self):
        if self.pconn is not None:
            self.conn = self.pconn
        else:
            self.conn = await DatabaseConnection.db_pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.pconn is None:
            await DatabaseConnection.db_pool.release(self.conn)

    @staticmethod
    async def init_db_pool():
        DatabaseConnection.db_pool = await asyncpg.create_pool(**dbcfg)
        print("db_pool inited.")
