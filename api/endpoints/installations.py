from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
import models.installations
import common
from I4cAPI import I4cApiRouter
from models import ProjectVersionStatusEnum, InstallationStatusEnum

router = I4cApiRouter(include_path="/installations")


@router.post("/{project}/{version}", response_model=models.installations.Installation, x_properties=dict(object="installations", action="new"))
async def new_installation(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/installations/{project}/{version}")),
    project: str = Path(...),
    version: str = Path(...),
    statuses: Optional[List[ProjectVersionStatusEnum]] = Query(None, description="Allowed project statuses, default [final]")
):
    return await models.installations.new_installation(credentials, project, version, statuses)


@router.get("", response_model=List[models.installations.Installation], x_properties=dict(object="installations", action="list"))
async def list_installation(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/installations")),
    id: Optional[int] = Query(None),
    status: Optional[InstallationStatusEnum] = Query(None),
    after: Optional[datetime] = Query(None, title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    before: Optional[datetime] = Query(None, title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    project_name: Optional[str] = Query(None),
    ver: Optional[int] = Query(None),
):
    return await models.installations.get_installations(credentials, id, status, after, before, project_name, ver)


@router.patch("/{id}", response_model=models.common.PatchResponse, x_properties=dict(object="installations", action="patch"))
async def patch_installation(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/installations/{name}")),
    id: int = Path(...),
    patch: models.installations.InstallationPatchBody = Body(...),
):
    return await models.installations.patch_installation(credentials, id, patch)


@router.get("/{id}/{savepath:path}", x_properties=dict(object="installations", action="get_file"))
async def installation_get_file(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/installations/{id}/{savepath:path}")),
    id: int = Path(...),
    savepath: str = Path(...),
):
    savepath = models.projects.ProjFile.check_savepath(savepath)
    return await models.installations.installation_get_file(credentials, id, savepath)
