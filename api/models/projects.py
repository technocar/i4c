import os
import json
from enum import Enum
from textwrap import dedent
from typing import List, Dict, Optional
from pydantic import Field, validator
from common import DatabaseConnection, I4cBaseModel, write_debug_sql
from common.exceptions import I4cInputValidationError, I4cClientError
from models import ProjectStatusEnum, ProjectVersionStatusEnum
from models.common import PatchResponse
import common.db_helpers


class Project(I4cBaseModel):
    """Collection of programs needed for machining a product."""
    name: str = Field(..., title="Name.")
    status: ProjectStatusEnum = Field(..., title="Status.")
    versions: List[str] = Field(..., title="List of versions. Numbers are version numbers, others are labels.")
    extra: Optional[Dict[str, str]] = Field({}, title="Additional data, e.g. external identifiers.")


class ProjectPatchCondition(I4cBaseModel):
    flipped: Optional[bool] = Field(None, title="Pass if the condition is not met.")
    status: Optional[List[ProjectStatusEnum]] = Field(None, title="Has any of the listed statuses.")
    extra: Optional[Dict[str, str]] = Field(None, title="All the listed extra values are set and match.")
    has_extra: List[str] = Field(None, title="Has the listed extra values.")  # TODO check if all keys exist

    def match(self, project:Project):
        r = ( ((self.status is None) or (project.status in self.status))
              and (self.extra is None) or all(project.extra[k] == v for (k, v) in self.extra.items())
              and (self.has_extra is None) or all(k in project.extra for k in self.has_extra.keys()))
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class ProjectPatchChange(I4cBaseModel):
    """Change to a project."""
    status: Optional[ProjectStatusEnum] = Field(None, title="Set the status.")
    extra: Optional[Dict[str,str]] = Field(None, title="Add extra values.")
    # TODO set_extra del_extra

    def is_empty(self):
        return self.status is None and self.extra is None


class ProjectPatchBody(I4cBaseModel):
    """Update to a project. If all conditions are met, the change is carried out."""
    conditions: Optional[List[ProjectPatchCondition]] = Field([], title="Conditions evaluated before the change.")
    change: ProjectPatchChange = Field(..., title="Changes.")


class ProjectIn(I4cBaseModel):
    """Collection of programs needed for machining a product. Input."""
    name: str
    status: ProjectStatusEnum = Field("active")
    # todo 5: This should be Optional[Dict[str,str]] insted of json data.
    extra: Optional[str]


class GitFile(I4cBaseModel):
    """File in a GIT repository."""
    repo: str = Field(..., title="Address of the repository.")
    name: str = Field(..., title="File name with relative path if needed.")
    commit: str = Field(..., title="Id of the commit.")

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


class UncFile(I4cBaseModel):
    """File on the network. Version control is not provided, use folders or file name elements."""
    name: str = Field(..., title="Full path and name.")

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


class IntFile(I4cBaseModel):
    """Internalized file. Can be managed with the intfile endpoints."""
    name: str = Field(..., title="Logical name.")
    ver: int = Field(..., title="Version number.")

    def __eq__(self, other):
        if not isinstance(other, IntFile):
            return False
        return (self.name == other.name
                and self.ver == other.ver)

    async def get_intfile_id(self, conn):
        sql = "select id from file_int where name = $1 and ver = $2"
        res = await conn.fetchrow(sql, self.name, self.ver)
        if res:
            return res[0]
        return None


class ProjFile(I4cBaseModel):
    """File in the project. Exactly one of file_git, file_unc and file_int must be provided."""
    savepath: str = Field(..., title="Logical name of the target file.")
    file_git: Optional[GitFile] = Field(None, title="GIT file.")
    file_unc: Optional[UncFile] = Field(None, title="Network file.")
    file_int: Optional[IntFile] = Field(None, title="Internal file.")

    @validator('savepath')
    def check_savepath(cls, v):
        if v is None:
            return v
        v = os.path.normpath(v).replace('\\', '/')
        parts = v.split('/')
        if '..' in parts:
            raise I4cInputValidationError('invalid path')
        return v

    def __eq__(self, other):
        if not isinstance(other, ProjFile):
            return False

        def check_with_null(a,b):
            return (a is None and b is None) or (a == b)

        return (self.savepath == other.savepath
                and check_with_null(self.file_git, other.file_git)
                and check_with_null(self.file_unc, other.file_unc)
                and check_with_null(self.file_int, other.file_int)
                )

    async def insert_to_db(self, conn, pv_id):
        git_id = (await self.file_git.insert_to_db(conn)) if self.file_git is not None else None
        unc_id = (await self.file_unc.insert_to_db(conn)) if self.file_unc is not None else None
        if self.file_int is not None:
            int_id = await self.file_int.get_intfile_id(conn)
            if int_id is None:
                raise I4cClientError("Internal file is not loaded to db. Load first.")
        else:
            int_id = None

        sql_insert = "insert into project_file (project_ver, savepath, file_git, file_unc, file_int) values ($1, $2, $3, $4, $5)"
        await conn.execute(sql_insert, pv_id, self.savepath, git_id, unc_id, int_id)


class FileWithProjInfo(ProjFile):
    """Result of file search."""
    project_name: str = Field(..., title="Containing project.")
    project_ver: int = Field(..., title="Containing project version.")


class ProjectVersion(I4cBaseModel):
    """
    Project version. Projects are subject to versioning. Projects in use can't be changed, but new versions can be
    created. Versions can be labeled.
    """
    ver: int = Field(..., title="Version number.")
    labels: List[str] = Field(..., title="List of labels.")
    status: ProjectVersionStatusEnum = Field(..., title="Status.")
    files: List[ProjFile] = Field(..., title="Contained files.")


class ProjectVersionPatchCondition(I4cBaseModel):
    """Condition to a project version update."""
    flipped: Optional[bool] = Field(False, title="Pass if the condition is not met.")
    status: Optional[List[ProjectVersionStatusEnum]] = Field(None, title="Has any of the listed statuses.")
    has_label: Optional[bool] = Field(None, title="Has any labels set.")
    exist_label: Optional[str] = Field(None, title="Has the label.")
    exist_label_in_proj: Optional[str] = Field(None, title="The label is set on any versions of the project.")

    def match(self, pv:ProjectVersion, pi: Project):
        r = ((self.status is None) or (pv.status in self.status)) \
            and ((self.has_label is None) or (len(pv.labels) > 0)) \
            and ((self.exist_label is None) or (self.exist_label in pv.labels)) \
            and ((self.exist_label_in_proj is None)
                 or ((self.exist_label_in_proj in pi.versions) if pi is not None else False))
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class ProjectVersionPatchChange(I4cBaseModel):
    """Change to a project version. Unset members are ignored."""
    status: Optional[ProjectVersionStatusEnum] = Field(None, title="New status.")
    clear_label: Optional[List[str]] = Field(None, title="Remove the labels.")
    set_label: Optional[List[str]] = Field(None, title="Set the labels.")
    add_file: Optional[List[ProjFile]] = Field(None, title="Add files.")
    del_file: Optional[List[str]] = Field(None, title="Remove files.")

    def is_empty(self):
        return ( self.status is None
               and self.clear_label is None
               and self.set_label is None
               and self.add_file is None
               and self.del_file is None)


class ProjectVersionPatchBody(I4cBaseModel):
    """Update to a project version. Conditions are evaluated, and if met, change is carried out."""
    conditions: List[ProjectVersionPatchCondition] = Field([], title="Conditions to be evaluated before the change.")
    change: ProjectVersionPatchChange = Field(..., title="Change to be carried out.")


class GetProjectsVersions(Enum):
    all = 0
    labels_only = 1
    versions_only = 2


async def get_projects(credentials, name=None, name_mask=None, status=None, file=None, *, pconn=None,
                       versions:GetProjectsVersions = GetProjectsVersions.all):
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
                <versions_only>
                group by v.project),
            res as (
                select 
                  p.name, 
                  p.status, 
                  coalesce(array_cat(pv.versions, pl.versions), ARRAY[]::character varying (200)[]) as versions, 
                  p.extra
                from projects p
                left join pv on pv.project = p.name
                left join pl on pl.project = p.name
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
        if name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(name_mask, "res.name", params)
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if file is not None:
            params.append(file)
            sql += f" and exists(select * from rf where rf.project = res.name and rf.savepath = ${len(params)})"
        sql = sql.replace("<labels_only>", "where False" if versions == GetProjectsVersions.labels_only else "") \
                 .replace("<versions_only>", "where False" if versions == GetProjectsVersions.versions_only else "")
        write_debug_sql("get_projects.sql", sql, *params)
        res = await conn.fetch(sql, *params)
        res = [{k: (v if k != "extra" else json.loads(v)) for (k, v) in row.items()} for row in res] # TODO how pathetic is that? why does it return a string?
        return res


async def new_project(credentials, project):
    if len(await get_projects(credentials, project.name)) > 0:
        raise I4cClientError("Project name is not unique")

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
                raise I4cClientError("Project not found")
            project = Project(**project[0])

            match = True
            for cond in patch.conditions:
                match = cond.match(project)
                if not match:
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
                params.append(json.dumps(patch.change.extra))    # TODO pathetic vol 2: why do we need dumps
                sql += f"{sep}\"extra\"=${len(params)}"
                sep = ",\n"
            sql += "\nwhere name = $1"

            await conn.execute(sql, *params)
            return PatchResponse(changed=True)


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
            left join file_unc on file_unc.id = pf.file_unc
            left join file_int on file_int.id = pf.file_int
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
            select 
              pv.id as project_ver, 
              pv.ver, 
              coalesce(pl.labels, array[]::varchar[]) labels, 
              pv.status, 
              coalesce(rf.files, array[]::varchar[]) files
            from project_version pv
            left join pl on pl.project = pv.project and pl.ver = pv.ver
            left join rf on rf.project_ver = pv.id
            where pv.project = $1 and pv.ver = $2::int
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetch(sql, project, ver)
        if len(res) == 0:
            raise I4cClientError("Project version not found")
        res = res[0]
        p = ProjectVersion(ver=res["ver"], labels=res["labels"], status=res["status"], files=[])
        for savepath in res["files"]:
            p.files.append(await get_proj_file(res["project_ver"], savepath, pconn=conn))
        return p, res["project_ver"]


async def post_projects_version(credentials, project_name, ver, files):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            pi = await get_projects(credentials, project_name, pconn=conn, versions=GetProjectsVersions.versions_only)
            pv = Project(**pi[0]).versions if len(pi) > 0 else []
            if ver is None:
                ver = 1
                for v in pv:
                    ver = max((ver, int(v)+1))
            else:
                if str(ver) in pv:
                    raise I4cClientError("Project version conflicts")
            sql_insert = dedent("""\
                insert into project_version (project, ver, status) values ($1, $2, $3)
                returning id
            """)
            pv_id = (await conn.fetchrow(sql_insert, project_name, ver, ProjectVersionStatusEnum.edit))[0]
            for l in files:
                await l.insert_to_db(conn, pv_id)

            return ProjectVersion(ver=ver, labels=[], status=ProjectVersionStatusEnum.edit, files=files)


async def patch_project_version(credentials, project_name, ver, patch: ProjectVersionPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            pv, pv_id = await get_projects_version(credentials, project_name, ver, pconn=conn)
            pi = await get_projects(credentials, project_name, pconn=conn, versions=GetProjectsVersions.labels_only)
            pi = pi[0] if len(pi) > 0 else None

            match = True
            for cond in patch.conditions:
                match = cond.match(pv, pi)
                if not match:
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
                        # todo 3: check this. This moves here ALL label of this kind from this project.
                        #         Probably there are maximum 1 per project, but semms to be safer to
                        #         move one and delete the others.
                        for r in res_chec:
                            if r["project_ver"] != pv_id:
                                await conn.execute(sql_update, pv_id, r["project_ver"], l)
                    else:
                        await conn.execute(sql_insert, pv_id, l)

            if patch.change.del_file:
                # todo: delete data from extension tables (file_git, file_unc)?
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
                            raise I4cClientError("Project file with same savepath and different properties exists")

            return PatchResponse(changed=True)


async def files_list(credentials, proj_name, projver, save_path, save_path_mask,
                     protocol, name, name_mask, repo, repo_mask, commit, commit_mask, filever, *, pconn=None) \
        -> List[FileWithProjInfo]:
    sql = dedent("""\
            with
                res as (
                    SELECT 
                      pv.project as proj_name,
                      pv.ver as proj_ver,
                      pf.savepath as save_path,
                      coalesce(CASE WHEN pf.file_git is not null then 'git' end,
                               CASE WHEN pf.file_int is not null then 'int' end,
                               CASE WHEN pf.file_unc is not null then 'unc' end) as "protocol",
                      coalesce(fg.name, fi.name, fu.name) as name,
                      fg.repo,
                      fg.commit,
                      fi.ver as filever,
                      
                      fg.id as git_id,
                      fg.repo as git_repo,
                      fg.name as git_name,
                      fg.commit as git_commit,
                    
                      fu.id as unc_id,
                      fu.name as unc_name,
                    
                      fi.id as int_id,
                      fi.name as int_name,
                      fi.ver as int_ver  
                    from project_file pf
                    join project_version pv on pv.id = pf.project_ver
                    left join file_git fg on fg.id = pf.file_git
                    left join file_int fi on fi.id = pf.file_int
                    left join file_unc fu on fu.id = pf.file_unc
                )
            select * 
            from res
            where True
          """)
    params = []

    def add_param(value, col_name, *, param_type=None):
        nonlocal sql
        nonlocal params
        if value is not None:
            params.append(value)
            sp = f"::{param_type}" if param_type else ""
            sql += f"and res.{col_name} = ${len(params)}{sp}\n"

    add_param(proj_name, "proj_name")
    add_param(projver, "proj_ver", param_type="int")
    add_param(save_path, "save_path")

    if save_path_mask is not None:
        sql += "and " + common.db_helpers.filter2sql(save_path_mask, "res.save_path", params)

    if protocol is not None:
        sql += 'and (False\n'
        for p in protocol:
            params.append(p)
            sql += f"or res.protocol=${len(params)}\n"
        sql += ')\n'
    add_param(name, "name")
    if name_mask is not None:
        sql += "and " + common.db_helpers.filter2sql(name_mask, "res.name", params)
    add_param(repo, "repo")
    if repo_mask is not None:
        sql += "and " + common.db_helpers.filter2sql(repo_mask, "res.repo", params)
    add_param(commit, "commit")
    if commit_mask is not None:
        sql += "and " + common.db_helpers.filter2sql(commit_mask, "res.commit", params)
    add_param(filever, "filever", param_type="int")
    async with DatabaseConnection(pconn) as conn:
        write_debug_sql('files_list.sql', sql, *params)
        dr = await conn.fetch(sql, *params)
        res = []
        for r in dr:
            d = dict(savepath=r["save_path"], project_name=r["proj_name"], project_ver=r["proj_ver"])
            if r["git_id"]:
                d["file_git"] = GitFile(repo=r["git_repo"], name=r["git_name"], commit=r["git_commit"])
            if r["unc_id"]:
                d["file_unc"] = UncFile(name=r["unc_name"])
            if r["int_id"]:
                d["file_int"] = IntFile(name=r["int_name"], ver=r["int_ver"])
            res.append(FileWithProjInfo(**d))
        return res
