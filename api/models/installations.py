from textwrap import dedent
from typing import List, Optional

from fastapi import HTTPException

from common import DatabaseConnection, write_debug_sql
from pydantic import BaseModel, Field
from datetime import datetime
from models import ProjectVersionStatusEnum, InstallationStatusEnum, ProjectStatusEnum


class Installations(BaseModel):
    id: int
    ts: datetime
    project: str
    invoked_version: str
    real_version: int
    status: str
    status_msg: Optional[str]
    files: List[str] = Field([])


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
    sql_insert_installation = dedent("""\
         insert into installation 
           ("timestamp", project, invoked_version, real_version, status) 
         values 
           (current_timestamp, $1, $2, $3, $4)
         returning id, "timestamp", status, status_msg
         """)
    sql_insert_installation_file = dedent("""\
         insert into installation_file 
           (installation, savepath) 
         values 
           ($1, $2)""")
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

                write_debug_sql('insert_installation.sql', sql_insert_installation, project, version, i["real_version"], InstallationStatusEnum.todo)

                db_insert_installation = await conn.fetchrow(sql_insert_installation, project, version, i["real_version"], InstallationStatusEnum.todo)
                i["id"] = db_insert_installation[0]
                i["ts"] = db_insert_installation[1]
                i["status"] = db_insert_installation[2]
                i["status_msg"] = db_insert_installation[3]

                i["files"] = []
                for db_project_file in db_project_files:
                    i["files"].append(db_project_file[0])
                    write_debug_sql('sql_insert_installation_file.sql', sql_insert_installation_file, i["id"], db_project_file[0])
                    await conn.execute(sql_insert_installation_file, i["id"], db_project_file[0])

                return i
            else:
                raise HTTPException(status_code=400, detail="No project found")
