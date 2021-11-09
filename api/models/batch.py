from datetime import datetime
from common import I4cBaseModel, DatabaseConnection


class ListItem(I4cBaseModel):
    batch: str
    first: datetime
    last: datetime
    count: int


batch_list_sql = open("models\\batch_list.sql").read()


async def batch_list(credentials, project, after, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetch(batch_list_sql, project, after)
        return res
