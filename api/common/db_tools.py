from common import DatabaseConnection


async def get_user_customer(user_id, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = """select customer from "user" where "id" = $1"""
        res = await conn.fetchrow(sql, user_id)
        if not res:
            return None
        return res[0]
