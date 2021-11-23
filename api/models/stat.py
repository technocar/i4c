from datetime import datetime
from common import I4cBaseModel, DatabaseConnection


class StatDef(I4cBaseModel):
    id: int


async def stat_list(credentials, user=None, name=None, name_mask=None, type=None, *, pconn=None):
    # todo 1: **********
    res = []
    for i in range(1,5):
        res.append(StatDef(id=i))
    return res
