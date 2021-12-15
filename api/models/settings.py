from typing import Optional
from common import I4cBaseModel, DatabaseConnection
from common.exceptions import I4cClientNotFound


class ValueIn(I4cBaseModel):
    value: Optional[str]


async def settings_get(credentials, key, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = """select "value" from settings where "key" = $1"""
        res = await conn.fetchrow(sql, key)
        if res:
            return res[0]
        raise I4cClientNotFound("Key not found")


async def settings_put(credentials, key, value: ValueIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            await settings_get(credentials, key, pconn=conn)
            sql = """update settings set "value" = $2 where "key"= $1"""
            await conn.execute(sql, key, value.value)
