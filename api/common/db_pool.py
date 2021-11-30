import asyncpg
from .common_obj import dbcfg, log


class DatabaseConnection:
    db_pool = None
    conn_id_generator = 0
    __slots__ = ['pconn', 'conn', 'conn_id']

    def __init__(self, pconn=None):
        self.pconn = pconn
        self.conn = None
        self.conn_id = None

    async def __aenter__(self) -> asyncpg.connection.Connection:
        if self.pconn is not None:
            self.conn = self.pconn
        else:
            DatabaseConnection.conn_id_generator += 1
            self.conn_id = DatabaseConnection.conn_id_generator
            log.debug(f"acquiring db connection {self.conn_id}")
            self.conn = await DatabaseConnection.db_pool.acquire()
            log.debug(f"acquired db connection {self.conn_id} PID = {self.conn.get_server_pid()}")
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.pconn is None:
            log.debug(f"releasing db connection {self.conn_id}")
            await DatabaseConnection.db_pool.release(self.conn)
            log.debug(f"released db connection {self.conn_id}")

    @staticmethod
    async def init_db_pool():
        DatabaseConnection.db_pool = await asyncpg.create_pool(**dbcfg)
        log.info("db_pool inited.")
