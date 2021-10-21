from fastapi import HTTPException
from common import MyBaseModel, DatabaseConnection

view_last_instance_sql = open("models\\last_instance.sql").read()


class LastInstance(MyBaseModel):
    instance: str
    sequence: str


async def get_last_instance(credentials, device, *, pconn=None):
    try:
        async with DatabaseConnection(pconn) as conn:
            return await conn.fetchrow(view_last_instance_sql, device)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")
