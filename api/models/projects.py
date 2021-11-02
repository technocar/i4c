from textwrap import dedent
from typing import List, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel, Field

from common import DatabaseConnection
from models import ProjectStatusEnum, ProjectVersionStatusEnum
from models.common import PatchResponse


class Project(BaseModel):
    name: str
    status: ProjectStatusEnum
    versions: List[str] = Field(..., title="List of versions. Numbers are version numbers others are labels.")
    extra: str


class ProjectPatchCondition(BaseModel):
    status: Optional[ProjectStatusEnum]
    extra: Optional[str]

    def match(self, project:Project):
        return (
                ((self.status or project.status) == project.status)
                and ((self.extra or project.extra) == project.extra)
        )


class ProjectPatchChange(BaseModel):
    status: Optional[ProjectStatusEnum]
    extra: Optional[str]

    def is_empty(self):
        return self.status is None and self.extra is None


class ProjectPatchBody(BaseModel):
    conditions: List[ProjectPatchCondition]
    change: ProjectPatchChange


class ProjectIn(BaseModel):
    name: str
    status: ProjectStatusEnum
    extra: Optional[str]


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
    file_git: Optional[GitFile]
    file_unc: Optional[UncFile]
    file_int: Optional[IntFile]


class ProjectVersion(BaseModel):
    ver: int = Field(..., title="Version number.")
    labels: List[str] = Field(..., title="List of labels.")
    status: ProjectVersionStatusEnum
    files: List[ProjFile]


async def get_projects(credentials, name=None, status=None, file=None, *, pconn=None):
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
                  coalesce(array_cat(pv.versions, pl.versions), ARRAY[]::character varying (200)[]) as versions, 
                  p.extra
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
    async with DatabaseConnection(pconn) as conn:
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
        res = await conn.fetch(sql, *params)
        return res


async def new_project(credentials, project):
    if len(await get_projects(credentials, project.name)) > 0:
        raise HTTPException(status_code=400, detail="Project name is not unique")

    sql_insert_project = dedent("""\
         insert into projects 
           (name, "status", "extra") 
         values 
           ($1, $2, $3)""")
    if project.status is None:
        project.status = ProjectStatusEnum.active
    async with DatabaseConnection() as conn:
        await conn.execute(sql_insert_project, project.name, project.status, project.extra)
        return (await get_projects(credentials, project.name, pconn=conn))[0]


async def patch_project(credentials, name, patch: ProjectPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            project = await get_projects(credentials, name, pconn=conn)
            if len(project) == 0:
                raise HTTPException(status_code=400, detail="Project not found")
            project = Project(**project[0])

            match = False
            for cond in patch.conditions:
                match = cond.match(project)
                if match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)
            params = [project.name]
            sql = "update projects\nset\n"
            sep = ""
            if patch.change.status:
                params.append(patch.change.status)
                sql += f"{sep}\"status\"=${len(params)}"
                sep = ",\n"
            if patch.change.extra:
                params.append(patch.change.extra)
                sql += f"{sep}\"extra\"=${len(params)}"
                sep = ",\n"
            sql += "\nwhere name = $1"

            await conn.execute(sql, *params)
            return PatchResponse(changed=True)

# todo 1: file search and intfiles api


async def get_proj_file(project_ver, savepath, *, pconn=None):
    sql = dedent("""\
            select 
              file_git.id as git_id,
              file_git.repo as git_repo,
              file_git.name as git_name,
              file_git.commit as git_commit,
              
              file_unc.id as unc_id,
              file_unc.name as unc_name,
              
              file_int.id as int_id,
              file_int.name as int_name,
              file_int.ver as int_ver
            from project_file pf
            left join file_git on file_git.id = pf.file_git
            left join file_unc on file_git.id = pf.file_unc
            left join file_int on file_git.id = pf.file_int
            where pf.project_ver = $1 and pf.savepath = $2
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetchrow(sql, project_ver, savepath)
        if res:
            d = dict(savepath=savepath)
            if res["git_id"]:
                d["git_file"] = GitFile(repo=res["git_repo"], name=res["git_name"], commit=res["git_commit"])
            if res["unc_id"]:
                d["unc_file"] = UncFile(name=res["unc_name"])
            if res["int_id"]:
                d["int_id"] = IntFile(name=res["int_name"], ver=res["int_ver"])
            return ProjFile(**d)
        return None


async def get_projects_version(credentials, project, ver, *, pconn=None):
    sql = dedent("""\
            with
            pl as (
                select v.project, v.ver, ARRAY_AGG(l.label) labels
                from project_version v
                join project_label l on l.project_ver = v.id
                group by v.project, v.ver),
            rf as (
                select pf.project_ver, ARRAY_AGG(pf.savepath) files
                from project_file pf
                group by pf.project_ver
                )
            select pv.id as project_ver, pv.ver, pl.labels, pv.status, rf.files
            from project_version pv
            left join pl on pl.project = pv.project and pl.ver = pv.ver
            left join rf on rf.project_ver = pv.id
            where pv.project = $1 and pv.ver = $2
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetch(sql, project, ver)
        if len(res) == 0:
            raise HTTPException(status_code=400, detail="Project version not found")
        res = res[0]
        p = ProjectVersion(ver=res["ver"], labels=res["labels"], status=res["status"], files=[])
        for savepath in res["files"]:
            p.files.append(await get_proj_file(res["project_ver"], savepath, pconn=conn))
        return p


async def post_projects_version(credentials, name, ver, files):
    # todo 1: **********
    pass
