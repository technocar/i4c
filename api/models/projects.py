from textwrap import dedent
from typing import List, Optional

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
    # todo: see c:\Users\gygyor\PycharmProjects\_TutorialFun\git_test\main.py
    repo: str
    name: str
    commit: str

    def __eq__(self, other):
        if not isinstance(other, GitFile):
            return False
        return (self.repo == other.repo
                and self.name == other.name
                and self.commit == other.commit)

    async def insert_to_db(self, conn):
        sql_insert = dedent("""\
            insert into file_git (repo, name, commit) values ($1, $2, $3)
            returning id
            """)
        return (await conn.fetchrow(sql_insert, self.repo, self.name, self.commit))[0]


class UncFile(BaseModel):
    name: str

    def __eq__(self, other):
        if not isinstance(other, UncFile):
            return False
        return self.name == other.name

    async def insert_to_db(self, conn):
        sql_insert = dedent("""\
            insert into file_unc (name) values ($1)
            returning id
            """)
        return (await conn.fetchrow(sql_insert, self.name))[0]


class IntFile(BaseModel):
    name: str
    ver: str

    def __eq__(self, other):
        if not isinstance(other, IntFile):
            return False
        return (self.name == other.name
                and self.ver == other.ver)


class ProjFile(BaseModel):
    savepath: str
    file_git: Optional[GitFile]
    file_unc: Optional[UncFile]
    file_int: Optional[IntFile]

    def __eq__(self, other):
        if not isinstance(other, ProjFile):
            return False

        def check_with_null(a,b):
            return (a is None and b is None) or (a==b)

        return (self.savepath == other.savepath
                and check_with_null(self.file_git, other.file_git)
                and check_with_null(self.file_unc, other.file_unc)
                and check_with_null(self.file_int, other.file_int)
                )

    async def insert_to_db(self, conn, pv_id):
        git_id = (await self.file_git.insert_to_db(conn)) if self.file_git is not None else None
        unc_id = (await self.file_unc.insert_to_db(conn)) if self.file_unc is not None else None
        if self.file_int is not None:
            raise HTTPException(status_code=400, detail="Unable to insert internal project file. Use dedicated calls")

        sql_insert = "insert into project_file (project_ver, savepath, file_git, file_unc) values ($1, $2, $3, $4)"
        await conn.execute(sql_insert, pv_id, self.savepath, git_id, unc_id)


class ProjectVersion(BaseModel):
    ver: int = Field(..., title="Version number.")
    labels: List[str] = Field(..., title="List of labels.")
    status: ProjectVersionStatusEnum
    files: List[ProjFile]


class ProjectVersionPatchCondition(BaseModel):
    flipped: Optional[bool]
    status: Optional[ProjectVersionStatusEnum]
    has_label: Optional[bool]
    exist_label: Optional[str]
    exist_label_in_proj: Optional[str]

    def match(self, pv:ProjectVersion, pi: Project):
        r = ((self.status or pv.status) == pv.status) \
            and ((self.has_label is None) or (len(pv.labels) > 0)) \
            and ((self.exist_label is None) or (self.exist_label in pv.labels)) \
            and ((self.exist_label_in_proj is None) or (self.exist_label_in_proj in pi.versions))
        if self.flipped is None or self.flipped:
            return r
        else:
            return not r


class ProjectVersionPatchChange(BaseModel):
    status: Optional[ProjectVersionStatusEnum]
    clear_label: Optional[List[str]]
    set_label: Optional[List[str]]
    add_file: Optional[List[ProjFile]]
    del_file: Optional[List[str]]

    def is_empty(self):
        return ( self.status is None
               and self.clear_label is None
               and self.set_label is None
               and self.add_file is None
               and self.del_file is None)


class ProjectVersionPatchBody(BaseModel):
    conditions: List[ProjectVersionPatchCondition]
    change: ProjectVersionPatchChange


async def get_projects(credentials, name=None, status=None, file=None, *, pconn=None, labels_only=False):
    sql = dedent("""\
            with pv as (
                select project, ARRAY_AGG(ver::"varchar"(200)) versions
                from project_version
                <labels_only>
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
        res = await conn.fetch(sql.replace("<labels_only>", "where False" if labels_only else ""),
                               *params)
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
                d["file_git"] = GitFile(repo=res["git_repo"], name=res["git_name"], commit=res["git_commit"])
            if res["unc_id"]:
                d["file_unc"] = UncFile(name=res["unc_name"])
            if res["int_id"]:
                d["file_int"] = IntFile(name=res["int_name"], ver=res["int_ver"])
            r = ProjFile(**d)
            return r
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
            where pv.project = $1 and pv.ver = $2::int
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetch(sql, project, ver)
        if len(res) == 0:
            raise HTTPException(status_code=400, detail="Project version not found")
        res = res[0]
        p = ProjectVersion(ver=res["ver"], labels=res["labels"], status=res["status"], files=[])
        for savepath in res["files"]:
            p.files.append(await get_proj_file(res["project_ver"], savepath, pconn=conn))
        return p, res["project_ver"]


async def post_projects_version(credentials, name, ver, files):
    # todo 1: **********
    pass


async def patch_project_version(credentials, project_name, ver, patch: ProjectVersionPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            pv, pv_id = await get_projects_version(credentials, project_name, ver, pconn=conn)
            pi = await get_projects(credentials, project_name, pconn=conn, labels_only=True)

            match = False
            for cond in patch.conditions:
                match = cond.match(pv, pi)
                if match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)
            params = [pv_id]
            sql = "update project_version\nset\n"
            sep = ""
            if patch.change.status:
                params.append(patch.change.status)
                sql += f"{sep}\"status\"=${len(params)}"
                sep = ",\n"
            sql += "\nwhere id = $1::int"
            if len(params) > 1:
                await conn.execute(sql, *params)

            if patch.change.clear_label:
                sql = dedent("""\
                    delete from project_label
                    where 
                      project_ver = $1
                      and label = $2
                """)
                for l in patch.change.clear_label:
                    await conn.execute(sql, pv_id, l)

            if patch.change.set_label:
                sql_check = dedent("""\
                    select pv.id as project_ver 
                    from project_label pl
                    join project_version pv on pv.id = pl.project_ver
                    where 
                      pv.project = $1
                      and label = $2
                """)
                sql_insert = dedent("""\
                    insert into project_label 
                       (project_ver, label) 
                    values 
                       ($1, $2)
                """)
                sql_update = dedent("""\
                    update project_label
                    set project_ver = $1
                    where 
                      project_ver = $2
                      and label = $3 
                """)
                for l in patch.change.set_label:
                    res_chec = await conn.fetch(sql_check, project_name, l)
                    if res_chec:
                        for r in res_chec:
                            if r["project_ver"] != pv_id:
                                await conn.execute(sql_update, r["project_ver"], pv_id, l)
                    else:
                        await conn.execute(sql_insert, pv_id, l)

            if patch.change.del_file:
                # todo: delete details (file_git, file_unc, file_int)?
                sql = dedent("""\
                    delete from project_file
                    where 
                      project_ver = $1
                      and savepath = $2
                """)
                for l in patch.change.del_file:
                    await conn.execute(sql, pv_id, l)

            if patch.change.add_file:
                for l in patch.change.add_file:
                    del_files = patch.change.del_file if patch.change.del_file is not None else []
                    old_proj_file = (await get_proj_file(pv_id, l.savepath, pconn=conn)) if l.savepath not in del_files else None
                    if old_proj_file is None:
                        await l.insert_to_db(conn, pv_id)
                    else:
                        if old_proj_file != l:
                            raise HTTPException(status_code=400, detail="Project file with same savepath and different properties exists")

            return PatchResponse(changed=True)
