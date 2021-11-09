import io
from textwrap import dedent
from typing import List, Optional

from fastapi import HTTPException
from starlette.responses import StreamingResponse, FileResponse

from common import I4cBaseModel, DatabaseConnection, write_debug_sql
from pydantic import Field
from datetime import datetime
from models import ProjectVersionStatusEnum, InstallationStatusEnum, ProjectStatusEnum
from models.common import PatchResponse


class Installation(I4cBaseModel):
    id: int
    ts: datetime
    project: str
    invoked_version: str
    real_version: int
    status: InstallationStatusEnum
    status_msg: Optional[str]
    files: List[str] = Field([])


class InstallationPatchCondition(I4cBaseModel):
    flipped: Optional[bool]
    status: Optional[List[InstallationStatusEnum]]

    def match(self, ins:Installation):
        r = ((self.status is None) or (ins.status in self.status))
        if self.flipped is None or self.flipped:
            return r
        else:
            return not r


class InstallationPatchChange(I4cBaseModel):
    status: Optional[InstallationStatusEnum]
    status_msg: Optional[str]

    def is_empty(self):
        return self.status is None and self.status_msg is None


class InstallationPatchBody(I4cBaseModel):
    conditions: List[InstallationPatchCondition]
    change: InstallationPatchChange



async def new_installation(credentials, project, version,
                           statuses: List[ProjectVersionStatusEnum]):
    if statuses is None:
        statuses = [ProjectVersionStatusEnum.final]
    sql_project = dedent("""\
        select *
        from projects
        where name = $1""")
    sql_project_version = dedent("""\
        select *
        from project_version v
        where 
          v.project = $1 
          and v.ver = $2
        """)
    sql_project_version_label = dedent("""\
        select v.ver
        from project_version v
        join project_label l on l.project_ver = v.id
        where 
          v.project = $1 
          and l.label = $2
        """)
    sql_project_files = dedent("""\
        select pf.savepath
        from project_file pf
        join project_version pv on pv.id = pf.project_ver
        where 
          pv.project = $1
          and pv.ver = $2
        """)
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            db_proj = await conn.fetchrow(sql_project, project)
            if db_proj:
                i = dict(project=project, invoked_version=version)
                if db_proj["status"] != ProjectStatusEnum.active:
                    raise HTTPException(status_code=400, detail="Not active project")
                try:
                    i["real_version"] = int(version)
                except ValueError:
                    db_project_version = await conn.fetchrow(sql_project_version_label, project, version)
                    if db_project_version:
                        i["real_version"] = db_project_version[0]
                    else:
                        raise HTTPException(status_code=400, detail="No matching project label found")

                db_project_version = await conn.fetchrow(sql_project_version, project, i["real_version"])
                if db_project_version:
                    if db_project_version["status"] not in statuses:
                        raise HTTPException(status_code=400, detail="Not matching project version status")
                else:
                    raise HTTPException(status_code=400, detail="No project version found")

                db_project_files = await conn.fetch(sql_project_files, project, i["real_version"])

                sql_insert_installation = dedent("""\
                     insert into installation 
                       ("timestamp", project, invoked_version, real_version, status) 
                     values 
                       (current_timestamp, $1, $2, $3, $4)
                     returning id, "timestamp", status, status_msg
                     """)

                write_debug_sql('insert_installation.sql', sql_insert_installation, project, version, i["real_version"], InstallationStatusEnum.todo)

                db_insert_installation = await conn.fetchrow(sql_insert_installation, project, version, i["real_version"], InstallationStatusEnum.todo)
                i["id"] = db_insert_installation[0]
                i["ts"] = db_insert_installation[1]
                i["status"] = db_insert_installation[2]
                i["status_msg"] = db_insert_installation[3]

                sql_insert_installation_file = dedent("""\
                     insert into installation_file 
                       (installation, savepath) 
                     values 
                       ($1, $2)""")
                i["files"] = []
                for db_project_file in db_project_files:
                    i["files"].append(db_project_file[0])
                    write_debug_sql('insert_installation_file.sql', sql_insert_installation_file, i["id"], db_project_file[0])
                    await conn.execute(sql_insert_installation_file, i["id"], db_project_file[0])

                return i
            else:
                raise HTTPException(status_code=400, detail="No project found")


async def get_installations(credentials, id=None, status=None, after=None, before=None, project_name=None, ver=None, *, pconn=None):
    sql = dedent("""\
                with
                ifiles as (
                    select a.installation, ARRAY_AGG(a.savepath) files
                    from installation_file a
                    group by a.installation),
                res as (
                    select 
                      i.id,
                      i.timestamp as ts,
                      i.project,
                      i.invoked_version,
                      i.real_version,
                      i.status,
                      i.status_msg,
                      coalesce(ifiles.files, ARRAY[]::character varying (200)[]) as files
                    from installation i
                    left join ifiles on ifiles.installation = i.id
                    )
                select * from res
                where True
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if after is not None:
            params.append(after)
            sql += f"and res.ts >= ${len(params)}\n"
        if before is not None:
            params.append(before)
            sql += f"and res.ts <= ${len(params)}\n"
        if project_name is not None:
            params.append(project_name)
            sql += f"and res.project = ${len(params)}\n"
        if ver is not None:
            params.append(ver)
            sql += f"and res.real_version = ${len(params)}\n"
        sql += f"order by res.ts desc"
        res = await conn.fetch(sql, *params)
        return res


async def patch_installation(credentials, id, patch: InstallationPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            installation = await get_installations(credentials, id, pconn=conn)
            if len(installation) == 0:
                raise HTTPException(status_code=400, detail="Installation not found")
            installation = Installation(**installation[0])

            match = True
            for cond in patch.conditions:
                match = cond.match(installation)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)
            params = [installation.id]
            sql = "update installation\nset\n"
            sep = ""
            if patch.change.status:
                params.append(patch.change.status)
                sql += f"{sep}\"status\"=${len(params)}"
                sep = ",\n"
            if patch.change.status_msg:
                params.append(patch.change.status_msg)
                sql += f"{sep}\"status_msg\"=${len(params)}"
                sep = ",\n"
            sql += "\nwhere id = $1"

            await conn.execute(sql, *params)
            return PatchResponse(changed=True)


async def installation_get_file(credentials, id, savepath, *, pconn=None):
    sql = dedent("""\
            select pf.* 
            from installation i
            join installation_file f on f.installation = i.id
            join project_version pv on pv.project = i.project and pv.ver = i.real_version
            join project_file pf on pf.project_ver = pv.id and pf.savepath = f.savepath
            where 
              i.id = $1 -- */ 8
              and f.savepath = $2 -- */ 'file1'
          """)
    async with DatabaseConnection(pconn) as conn:
        pf = await conn.fetch(sql, id, savepath)
        if len(pf) == 0:
            raise HTTPException(status_code=400, detail="Installation file not found")
        pf = pf[0]

        # todo: get real file data
        #        FileResponse
        #        StreamingResponse

        x = 'sfjkgsdkf'
        return StreamingResponse(io.BytesIO(str.encode(x)), media_type="application/octet-stream",
                                 headers={"content-disposition": 'attachment; filename="aaa.txt"'})

        # return FileResponse("api.py", media_type="application/octet-stream", filename='aaa.txt')
