import datetime
from typing import Optional, List
from pydantic import Field
from common import I4cBaseModel, DatabaseConnection

view_meta_sql = open("models/log/meta.sql").read()
view_meta_event_values_sql = open("models/log/meta_event_values.sql").read()


class Meta(I4cBaseModel):
    """Information about the data types in the log."""
    device: str = Field(..., title="Originating device.")
    data_id: str = Field(..., title="Data type.")
    name: Optional[str] = Field(None, title="Vendor defined descriptive name.")
    nice_name: Optional[str] = Field(None, title="User readable name.")
    system1: Optional[str] = Field(None, title="Subsystem level 1.")
    system2: Optional[str] = Field(None, title="Subsystem level 2.")
    category: Optional[str] = Field(None, title="Category. Sample, event or condition.")
    type: Optional[str] = Field(None, title="Vendor supplied type.")
    subtype: Optional[str] = Field(None, title="Vendor supplied sub type.")
    unit: Optional[str] = Field(None, title="Measurement unit.")
    value_list: Optional[List[str]] = Field(None, title="Possible values.")


class EventValue:
    """Possible values of an event type."""
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
