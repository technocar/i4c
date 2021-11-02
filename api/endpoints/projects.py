from typing import Optional, List
from fastapi import Depends, Query, Path, HTTPException, Body
from fastapi.security import HTTPBasicCredentials
import models.projects
import models.common
import common
from I4cAPI import I4cApiRouter
from models import ProjectStatusEnum

router = I4cApiRouter()


@router.get("", response_model=List[models.projects.Project], x_properties=dict(object="projects", action="list"))
async def list_projects(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects")),
    name: Optional[str] = Query(None),
    status: Optional[ProjectStatusEnum] = Query(None),
    file: Optional[str] = Query(None, description="Full savepath of the file.")
):
    return await models.projects.get_projects(credentials, name, status, file)


@router.get("/{name}", response_model=models.projects.Project, x_properties=dict(object="projects", action="get"))
async def get_project(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects/{name}")),
    name: str = Path(...),
):
    res = await models.projects.get_projects(credentials, name)
    if len(res) > 0:
        return res[0]
    raise HTTPException(status_code=404, detail="No record found")


@router.post("", response_model=models.projects.Project, x_properties=dict(object="projects", action="post"))
async def get_project(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/projects")),
    project: models.projects.ProjectIn = Body(...),
):
    return await models.projects.new_project(credentials, project)


@router.patch("/{name}", response_model=models.common.PatchResponse, x_properties=dict(object="projects", action="patch"))
async def get_project(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/projects/{name}")),
    name: str = Path(...),
    patch: models.projects.ProjectPatchBody = Body(...),
):
    return await models.projects.patch_project(credentials, name, patch)


@router.get("/{name}/v/{ver}", response_model=models.projects.ProjectVersion, x_properties=dict(object="projects ver", action="get"))
async def list_projects_version(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects/{name}/v/{ver}")),
    name: str = Path(...),
    ver: int = Path(...)
):
    return await models.projects.get_projects_version(credentials, name, ver)


@router.post("/{name}/v", response_model=models.projects.ProjectVersion, x_properties=dict(object="projects ver", action="post"))
async def post_projects_version(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/projects/{name}/v")),
    name: str = Path(...),
    ver: Optional[int] = Query(None),
    files: List[models.projects.ProjFile] = Body(...),
):
    return await models.projects.post_projects_version(credentials, name, ver, files)
