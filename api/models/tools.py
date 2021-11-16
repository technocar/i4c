from datetime import datetime, date, timedelta
from enum import Enum
from textwrap import dedent
from typing import Optional
from fastapi import HTTPException
from common import I4cBaseModel, DatabaseConnection
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


class ToolItem(I4cBaseModel):
    tool_id: Optional[str]
    type: Optional[str]
    count: int


async def patch_project_version(credentials, tool_id, patch:ToolsPatchBody, *, pconn=None):
    try:
        async with DatabaseConnection(pconn) as conn:
            sql = dedent("""\
                      insert into tools (id, \"type\")
                      values ($1, $2)
                      ON CONFLICT(id) DO UPDATE
                      SET \"type\" = EXCLUDED.\"type\";
                      """)
            await conn.execute(sql, tool_id, patch.change.type)
            return PatchResponse(changed=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")


async def tool_list(credentials):
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
