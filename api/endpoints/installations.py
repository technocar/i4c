from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import FileResponse
from starlette.requests import Request
import models.installations
import common
import models.common
import models.projects
from I4cAPI import I4cApiRouter
from models import ProjectVersionStatusEnum, InstallationStatusEnum

router = I4cApiRouter(include_path="/installations")


@router.post("/{project}/{version}", response_model=models.installations.Installation,
             operation_id="installation_start", summary="New installation.")
async def new_installation(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/installations/{project}/{version}")),
    project: str = Path(..., title="The project to install."),
    version: str = Path(..., title="The version to install. Can be a number, a label or `latest`."),
    statuses: Optional[List[ProjectVersionStatusEnum]] = Query(None, title="Check project status. If omitted, only final projects are allowed.")
):
    """
    Initiate an installation of the given project version. If you want to install a project that is not final, you have
    to use the statuses parameter.
    """
    return await models.installations.new_installation(credentials, project, version, statuses)


@router.get("", response_model=List[models.installations.Installation], operation_id="installation_list",
            summary="List installations.", features=['noaudit'])
async def list_installation(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/installations", ask_features=['noaudit'])),
    id: Optional[int] = Query(None),
    status: Optional[InstallationStatusEnum] = Query(None),
    after: Optional[datetime] = Query(None, title="After timestamp, iso format."),
    before: Optional[datetime] = Query(None, title="Before timestamp, iso format."),
    project_name: Optional[str] = Query(None, title="Exact name of the project."),
    ver: Optional[int] = Query(None, title="Project version."),
    # this is used on higher level only. See I4cApiRouter class.
    noaudit: bool = Query(False, title="Skip audit record", description="Will not write an audit record. Requires special privilege.")
):
    """
    List ongoing or previous installations.
    """
    return await models.installations.get_installations(credentials, id, status, after, before, project_name, ver)


@router.patch("/{id}", response_model=models.common.PatchResponse, operation_id="installation_update",
              summary="Update installation.")
async def patch_installation(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/installations/{id}")),
    id: int = Path(...),
    patch: models.installations.InstallationPatchBody = Body(...),
):
    """
    Applies changes to an existing installation if the conditions are met.
    """
    return await models.installations.patch_installation(credentials, id, patch)


@router.get("/{id}/{savepath:path}", response_class=FileResponse(..., media_type="application/octet-stream"),
            operation_id="installation_file", summary="Download a file.")
async def installation_get_file(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/installations/{id}/{savepath:path}")),
    id: int = Path(...),
    savepath: str = Path(...),
):
    """
    Retrieve a file that is part of the given installation. The list of files can be acquired via the installation
    record.
    """
    savepath = models.projects.ProjFile.check_savepath(savepath)
    return await models.installations.installation_get_file(credentials, id, savepath)
