from common import I4cBaseModel, DatabaseConnection


class AuditListItem(I4cBaseModel):
    """Audit of machining operations. Input."""
    pass


# todo 1: ****************
audit_list_sql = ""


# todo 1: ****************
async def audit_list(credentials, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        return await conn.fetch(audit_list_sql)
