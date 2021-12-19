import datetime
from typing import Optional, List
from common import I4cBaseModel, DatabaseConnection

view_meta_sql = open("models/log/meta.sql").read()
view_meta_event_values_sql = open("models/log/meta_event_values.sql").read()


class Meta(I4cBaseModel):
    device: str
    data_id: str
    name: Optional[str]
    nice_name: Optional[str]
    system1: Optional[str]
    system2: Optional[str]
    category: Optional[str]
    type: Optional[str]
    subtype: Optional[str]
    unit: Optional[str]
    value_list: Optional[List[str]]


class EventValue:
    data_id: str
    values: List[str]


async def get_meta(credentials, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        rs = await conn.fetch(view_meta_sql)

        after = datetime.date.today() + datetime.timedelta(-90)
        rs_event_values = await conn.fetch(view_meta_event_values_sql, after)

    l = {}
    for row in rs_event_values:
        key = (row["device"], row["data_id"])
        if key in l.keys():
            l[key].append(row["value"])
        else:
            l[key] = [row["value"]]

    res = [dict(row) for row in rs]

    for r in res:
        r["value_list"] = l[(r["device"], r["data_id"])] if (r["device"], r["data_id"]) in l.keys() else None

    return res
