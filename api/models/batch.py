from datetime import datetime
from common import I4cBaseModel, DatabaseConnection


class ListItem(I4cBaseModel):
    batch: str
    last: datetime


batch_list_sql = open("models\\batch_list.sql").read()
batch_list_noproject_sql = open("models\\batch_list_noproject.sql").read()


async def batch_list(credentials, project, after, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        if project is None:
            res = await conn.fetch(batch_list_noproject_sql, after)
        else:
            res = await conn.fetch(batch_list_sql, project, after)
        return res
