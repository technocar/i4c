from typing import Optional, List

from fastapi import Depends, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.projects
import models.users
from I4cAPI import I4cApiRouter
from models import FileProtocolEnum

router = I4cApiRouter()


@router.get("/login", response_model=models.users.UserResponse, tags=["user"], x_properties=dict(object="user", action="login"))
async def login(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/login"))):
    "Get user info based on login name"
    return await models.users.login(credentials)


@router.get("/files", response_model=List[models.projects.FileWithProjInfo], tags=["files"],
            x_properties=dict(object="files", action="list") )
async def files(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/files")),
        proj_name: Optional[str] = Query(None),
        projver: Optional[int] = Query(None),
        save_path: Optional[str] = Query(None),
        protocol: Optional[List[FileProtocolEnum]] = Query(None),
        name: Optional[str] = Query(None),
        repo: Optional[str] = Query(None),
        commit: Optional[str] = Query(None),
        filever: Optional[int] = Query(None),
):
    return await models.projects.files_list(credentials, proj_name, projver, save_path, protocol,
                                            name, repo, commit, filever)

