import io
import os
from textwrap import dedent
from typing import List, Optional
from starlette.responses import StreamingResponse, FileResponse
from common import I4cBaseModel, DatabaseConnection, write_debug_sql
from pydantic import Field
from datetime import datetime

from common.exceptions import I4cClientError, I4cClientNotFound
from models import ProjectVersionStatusEnum, InstallationStatusEnum, ProjectStatusEnum
from models.common import PatchResponse
from models.intfiles import get_internal_file_name
from models.projects import get_real_project_version


class Installation(I4cBaseModel):
    """Installation event. Serves as a request or an archive record of an installation."""
    id: int = Field(..., title="Identifier.")
    ts: datetime = Field(..., title="Timestamp of creation.")
    project: str = Field(..., title="Project to be installed.")
    invoked_version: str = Field(..., title="Project version number or label requested.")
    real_version: int = Field(..., title="Actual project version, label resolved.")
    status: InstallationStatusEnum = Field(..., title="Status of installation.")
    status_msg: Optional[str] = Field(..., title="Reason associated with the status.")
    files: List[str] = Field([], title="List of files to be installed.")


class InstallationPatchCondition(I4cBaseModel):
    """Conditions before an update to an installation."""
    flipped: Optional[bool] = Field(False, title="Pass if the condition is not met.")
    status: Optional[List[InstallationStatusEnum]] = Field(None, title="Has any of the given statuses.")

    def match(self, ins:Installation):
        r = ((self.status is None) or (ins.status in self.status))
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class InstallationPatchChange(I4cBaseModel):
    """Changes to an installation."""
    status: Optional[InstallationStatusEnum] = Field(None, title="Set the status.")
    status_msg: Optional[str] = Field(None, title="Set the status message.")

    def is_empty(self):
        return self.status is None and self.status_msg is None


class InstallationPatchBody(I4cBaseModel):
    """Update to an installation. The change will be carried out if all conditions are met."""
    conditions: Optional[List[InstallationPatchCondition]] = Field([], title="Conditions to check before the update.")
    change: InstallationPatchChange = Field(..., title="Change to be carried out.")


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
                    raise I4cClientError("Not active project")
                i["real_version"] = await get_real_project_version(project, version, pconn=conn)

                db_project_version = await conn.fetchrow(sql_project_version, project, i["real_version"])
                if db_project_version:
                    if db_project_version["status"] not in statuses:
                        raise I4cClientError("Not matching project version status")
                else:
                    raise I4cClientError("No project version found")

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
                raise I4cClientError("No project found")


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
                raise I4cClientError("Installation not found")
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


def get_git_file_content(repo, name, commit):
    def clone_repo(source_repo, target_folder, refspec, *, fetch_original=True):
        """
        :param source_repo: path to a bare or normal repo or url
        :param target_folder: empty folder to clone whole repo
        :param refspec: commit, branch, or tag
        :param fetch_original: if we should fetch on the source repo
        :return: None
        """
        if fetch_original:
            repo = git.Repo(source_repo)
            for origin in repo.remotes:
                origin.fetch(refspec)

        cloned_repo = git.Repo.clone_from(source_repo, target_folder, no_checkout=True)
        cloned_repo.git.checkout(refspec)

    import tempfile
    import git
    import os
    # todo 5: this clones the whole repo for each file, then deletes it. Maybe repos can be stored for longer.
    with tempfile.TemporaryDirectory() as t:  # creates a temp dir and deletes it afterward
        fetch_original = not repo.startswith("ssh://")
        clone_repo(repo, t, commit, fetch_original=fetch_original)
        file_path = os.sep.join([t, name])
        if os.path.isfile(file_path):
            with open(file_path, mode='rb') as file:
                return io.BytesIO(file.read())
        raise I4cClientNotFound("No file found")


async def installation_get_file(credentials, id, savepath, *, pconn=None):
    sql = dedent("""\
            select
              pf.file_git,
              pf.file_unc,
              pf.file_int,

              git.repo git_repo,
              git."name" git_name,
              git.commit git_commit,

              unc."name" unc_name,

              int."name" int_name,
              int.ver int_ver,
              int.content_hash int_content_hash
            from installation i
            join installation_file f on f.installation = i.id
            join project_version pv on pv.project = i.project and pv.ver = i.real_version
            join project_file pf on pf.project_ver = pv.id and pf.savepath = f.savepath
            left join file_git git on git.id = pf.file_git
            left join file_unc unc on unc.id = pf.file_unc
            left join file_int int on int.id = pf.file_int
            where
              i.id = $1 -- */ 8
              and f.savepath = $2 -- */ 'file1'
          """)
    async with DatabaseConnection(pconn) as conn:
        def get_checked_reponse(path, file_name):
            if os.path.isfile(path):
                return FileResponse(path,
                                    filename=file_name,
                                    media_type="application/octet-stream")
            raise I4cClientNotFound("No file found")

        pf = await conn.fetchrow(sql, id, savepath)
        if not pf:
            raise I4cClientError("Installation file not found")
        if pf["file_unc"] is not None:
            return get_checked_reponse(pf["unc_name"],savepath)
        if pf["file_int"] is not None:
            return get_checked_reponse(get_internal_file_name(pf["int_content_hash"]),savepath)
        if pf["file_git"] is not None:
            return StreamingResponse(get_git_file_content(pf["git_repo"], pf["git_name"], pf["git_commit"]),
                              media_type="application/octet-stream",
                              headers={"content-disposition": f'attachment; filename="{savepath}"'})
        raise I4cClientNotFound("No file found")
