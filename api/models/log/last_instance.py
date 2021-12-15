from common import I4cBaseModel, DatabaseConnection

view_last_instance_sql = open("models\\log\\last_instance.sql").read()


class LastInstance(I4cBaseModel):
    instance: str
    sequence: str


async def get_last_instance(credentials, device, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        return await conn.fetchrow(view_last_instance_sql, device)
