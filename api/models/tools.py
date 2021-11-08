from textwrap import dedent
from typing import Optional
from fastapi import HTTPException
from common import I4cBaseModel, DatabaseConnection


class ToolsPatchChange(I4cBaseModel):
    type: Optional[str]

    def is_empty(self):
        return self.type is None


class ToolsPatchBody(I4cBaseModel):
    change: ToolsPatchChange


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")
