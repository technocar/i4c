from typing import Optional, List

from fastapi import Depends, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.projects
import models.users
import models.roles
from I4cAPI import I4cApiRouter
from models import FileProtocolEnum

router = I4cApiRouter()


@router.get("/login", response_model=models.users.LoginUserResponse, tags=["user"], x_properties=dict(object="user", action="login"))
async def login(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/login"))):
    "Get user info based on login name"
    return await models.users.login(credentials)


@router.get("/privs", response_model=List[models.roles.Priv], tags=["roles"], x_properties=dict(object="roles", action="privs"))
async def privs(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/privs"))):
    "Get priv info"
    return await models.roles.get_priv(credentials)


@router.get("/files", response_model=List[models.projects.FileWithProjInfo], tags=["files"],
            x_properties=dict(object="files", action="list") )
async def files(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/files")),
        proj_name: Optional[str] = Query(None),
        projver: Optional[int] = Query(None),
        save_path: Optional[str] = Query(None),
        save_path_mask: Optional[List[str]] = Query(None),
        protocol: Optional[List[FileProtocolEnum]] = Query(None),
        name: Optional[str] = Query(None),
        name_mask: Optional[List[str]] = Query(None),
        repo: Optional[str] = Query(None),
        repo_mask: Optional[List[str]] = Query(None),
        commit: Optional[str] = Query(None),
        commit_mask: Optional[List[str]] = Query(None),
        filever: Optional[int] = Query(None),
):
    save_path = models.projects.ProjFile.check_savepath(save_path)
    save_path_mask = [s.replace('\\', '/') for s in save_path_mask]
    return await models.projects.files_list(credentials, proj_name, projver, save_path, save_path_mask,
                                            protocol, name, name_mask, repo, repo_mask, commit, commit_mask, filever)
