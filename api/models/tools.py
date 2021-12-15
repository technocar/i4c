from datetime import datetime, date, timedelta
from enum import Enum
from textwrap import dedent
from typing import Optional
from common import I4cBaseModel, DatabaseConnection
import models.log
from models.common import PatchResponse


class ToolsPatchChange(I4cBaseModel):
    type: Optional[str]

    def is_empty(self):
        return self.type is None


class ToolsPatchBody(I4cBaseModel):
    change: ToolsPatchChange


class ToolDataId(str, Enum):
    install_tool = "install_tool"
    remove_tool = "remove_tool"


class ToolDataPointKey(I4cBaseModel):
    timestamp: datetime
    sequence: int
    device: str
    data_id: ToolDataId


class ToolDataPoint(I4cBaseModel):
    timestamp: datetime
    sequence: int
    device: str
    data_id: ToolDataId
    tool_id: Optional[str]
    slot_number: Optional[str]


class ToolDataPointType(ToolDataPoint):
    type: Optional[str]


class ToolItem(I4cBaseModel):
    tool_id: Optional[str]
    type: Optional[str]
    count: int


async def patch_project_version(credentials, tool_id, patch:ToolsPatchBody, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
                  insert into tools (id, "type")
                  values ($1, $2)
                  ON CONFLICT(id) DO UPDATE
                  SET "type" = EXCLUDED."type";
                  """)
        await conn.execute(sql, tool_id, patch.change.type)
        return PatchResponse(changed=True)


async def tool_list(credentials, device, timestamp, sequence, max_count):
    if timestamp is None:
        timestamp = date.today() + timedelta(days=-365)
    if max_count is None:
        max_count = 1000

    async with DatabaseConnection() as conn:
        types_db = await conn.fetch("select id, \"type\" from tools")
        types = {}
        for t in types_db:
            types[t["id"]] = t["type"]

        logs_inst = await models.log.get_find(credentials, device, timestamp, sequence, name=ToolDataId.install_tool, after_count=max_count, pconn=conn)
        logs_del = await models.log.get_find(credentials, device, timestamp, sequence, name=ToolDataId.remove_tool, after_count=max_count, pconn=conn)
        res = []

        def merge(iterable1, iterable2, f):

            def next_eof(it):
                try:
                    return False, next(it)
                except StopIteration:
                    return True, None

            i1 = iter(iterable1)
            i2 = iter(iterable2)

            eof1, item1 = next_eof(i1)
            eof2, item2 = next_eof(i2)

            while not eof1 or not eof2:
                if eof1:
                    yield item2
                    eof2, item2 = next_eof(i2)
                elif eof2:
                    yield item1
                    eof1, item1 = next_eof(i1)
                else:
                    if f(item1, item2) < 0:
                        yield item1
                        eof1, item1 = next_eof(i1)
                    else:
                        yield item2
                        eof2, item2 = next_eof(i2)

        def f(a,b):
            if a.timestamp < b.timestamp:
                return -1
            if (a.timestamp == b.timestamp) and (a.sequence < b.sequence):
                return -1
            return 1

        for l in merge(logs_inst, logs_del, f):
            res.append(ToolDataPointType(
                timestamp=l.timestamp,
                sequence=l.sequence,
                device=l.device,
                data_id=l.data_id,
                tool_id=l.value_text,
                slot_number=l.value_extra,
                type=types.get(l.value_text)))
        return res


async def tool_list_usage(credentials):
    async with DatabaseConnection() as conn:
        sql = dedent("""\
                select
                  l.value_text "tool_id",
                  t.type,
                  count(*) "count"
                from public.log l
                left join tools t on t.id = l.value_text
                where
                  l.timestamp >= $1::timestamp with time zone -- */ '2021-08-23 07:56:00.957133+02'::timestamp with time zone
                  and l.data_id in ('install_tool', 'remove_tool')
                group by l.value_text, t.type
                order by 1,2
                """)
        return await conn.fetch(sql, date.today() + timedelta(days=-365))
