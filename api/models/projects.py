from datetime import datetime
from textwrap import dedent
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field

from common import DatabaseConnection
from models import ProjectStatusEnum, ProjectVersionStatusEnum


class KeyValue(BaseModel):
    key: str
    value: str


class Project(BaseModel):
    name: str
    status: ProjectStatusEnum
    versions: List[str] = Field(..., title="List of versions. Numbers are version numbers others are labels.")
    extra: List[KeyValue]
    created_at: datetime


class ProjectIn(BaseModel):
    name: str
    status: ProjectStatusEnum
    extra: Optional[List[Dict[str, str]]]


class GitFile(BaseModel):
    repo: str
    name: str
    commit: str


class UncFile(BaseModel):
    name: str


class IntFile(BaseModel):
    name: str
    ver: str


class ProjFile(BaseModel):
    savepath: str
    file: Union[GitFile, UncFile, IntFile]


class ProjectVersion(BaseModel):
    ver: int = Field(..., title="Version number.")
    labels: List[str] = Field(..., title="List of labels.")
    status: ProjectVersionStatusEnum
    files: List[ProjFile]


async def get_projects(credentials, name=None, status=None, file=None):
    sql = dedent("""\
            with pv as (
                select project, ARRAY_AGG(ver::"varchar"(200)) versions
                from project_version
                group by project),
            pl as (
                select v.project, ARRAY_AGG(l.label) versions
                from project_version v
                join project_label l on l.project_ver = v.id
                group by v.project),
            res as (
                select 
                  p.name, 
                  p.status, 
                  array_cat(pv.versions, pl.versions) as versions, 
                  p.extra, 
                  p.created_at
                from projects p
                left join pv on pv.project = p.name
                left join pl on pv.project = p.name
                ),
            rf as (
                select pv.project, pf.savepath
                from project_file pf
                join project_version pv on pv.id = pf.project_ver
                )
            select * from res
            where True
          """)
    async with DatabaseConnection() as conn:
        params = []
        if name is not None:
            params.append(name)
            sql += f"and res.name = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if file is not None:
            params.append(file)
            sql += f" and exists(select * from rf where rf.project = res.name and rf.savepath = ${len(params)})"
        return await conn.fetch(sql, *params)
