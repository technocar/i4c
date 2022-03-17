import re
from datetime import datetime
from textwrap import dedent
from typing import Optional, Dict, Any
from fastapi.security import HTTPBasicCredentials
from common import I4cBaseModel, DatabaseConnection, write_debug_sql
from pydantic import Field

from common.db_tools import asyncpg_rows_process_json


class AuditListItem(I4cBaseModel):
    """Audit event."""
    ts: datetime = Field(..., title="Exact time the data was collected.")
    user: Optional[str] = Field(None, title="Logged user.")
    ip: Optional[str] = Field(None, title="IP address.")
    obj: str = Field(..., title="Endpoint object.")
    action: Optional[str] = Field(None, title="Endpoint action.")
    extra: Optional[Dict[str,Any]] = Field(None, title="Other information")


async def audit_list(
        credentials: HTTPBasicCredentials,
        before: Optional[datetime],
        after: Optional[datetime],
        count: Optional[int],
        object: Optional[str],
        action: Optional[str],
        *,
        pconn=None):
    async with DatabaseConnection(pconn) as conn:
        params = []
        wheres = []
        limit = ""
        order_direction = ""
        if before is not None:
            params.append(before)
            wheres.append(f'and (l.timestamp <= ${len(params)})')
            order_direction = " desc" if after is None else ""

        if after is not None:
            params.append(after)
            wheres.append(f'and (l.timestamp >= ${len(params)})')

        if object is not None:
            params.append(object)
            wheres.append(f"and (left(l.data_id, length(${len(params)})+1) = ${len(params)}||'_')")

        if action is not None:
            params.append(action)
            wheres.append(f"and (right(l.data_id, length(${len(params)})+1) = '_'||${len(params)})")

        if count is not None:
            limit = f"limit {count}"

        sql = dedent(f"""
                select
                  l."timestamp" as ts,
                  l.data_id operation_id,
                  l.value_text "user",
                  l.value_extra ip,
                  l.value_aux extra
                from log l
                where
                    l.device='audit'
                    <wheres>
                order by
                    l.timestamp{order_direction}
                {limit}
                """)
        sql = sql.replace("<wheres>", '\n'.join(wheres))
        write_debug_sql("audit.sql", sql, *params)
        res = await conn.fetch(sql, *params)
        res = asyncpg_rows_process_json(res, 'extra')

        regex = re.compile(r"(?P<obj>[^_]+)_(?P<action>.+)")
        for i in res:
            match = regex.fullmatch(i["operation_id"])
            if match:
                i["obj"] = match.group("obj")
                i["action"] = match.group("action")
            else:
                i["obj"] = i["operation_id"]
                i["action"] = None

        return [AuditListItem(**r) for r in res]
