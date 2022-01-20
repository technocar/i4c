from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
import models.projects
import models.common
import common
from I4cAPI import I4cApiRouter
from common.exceptions import I4cClientNotFound
from models import ProjectStatusEnum

router = I4cApiRouter(include_path="/projects")


@router.get("", response_model=List[models.projects.Project], operation_id="project_list", summary="List projects.")
async def list_projects(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects")),
    name: Optional[str] = Query(None, title="Exact name."),
    name_mask: Optional[List[str]] = Query(None, title="Name search expression."),
    status: Optional[ProjectStatusEnum] = Query(None, title="Status."),
    file: Optional[str] = Query(None, description="Full savepath of the file.")
):
    """Get a filtered list of projects."""
    file = models.projects.ProjFile.check_savepath(file)
    return await models.projects.get_projects(credentials, name, name_mask, status, file)


@router.get("/{name}", response_model=models.projects.Project, operation_id="project_get", summary="Retrieve project.")
async def get_project(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects/{name}")),
    name: str = Path(...),
):
    """Retrieve a project by name."""
    res = await models.projects.get_projects(credentials, name)
    if len(res) > 0:
        return res[0]
    raise I4cClientNotFound("No record found")


@router.post("", response_model=models.projects.Project, operation_id="project_new", summary="Create project.")
async def new_project(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/projects")),
    project: models.projects.ProjectIn = Body(...),
):
    """Create a new project."""
    return await models.projects.new_project(credentials, project)


@router.patch("/{name}", response_model=models.common.PatchResponse, operation_id="project_update",
              summary="Update project.")
async def patch_project(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/projects/{name}")),
    name: str = Path(...),
    patch: models.projects.ProjectPatchBody = Body(...),
):
    """Change a project if conditions are met."""
    return await models.projects.patch_project(credentials, name, patch)


@router.get("/{name}/v/{ver}", response_model=models.projects.ProjectVersion, operation_id="project_ver_get")
async def get_projects_version(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects/{name}/v/{ver}")),
    name: str = Path(...),
    ver: str = Path(None, description="Version or label. `latest` for latest version.")
):
    """Retrieve a project version."""
    res, _ = await models.projects.get_projects_version(credentials, name, ver)
    return res


@router.post("/{name}/v", response_model=models.projects.ProjectVersion, operation_id="project_ver_new",
             summary="New project version.")
async def post_projects_version(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/projects/{name}/v")),
    name: str = Path(...),
    ver: Optional[int] = Query(None, title="A version number. Must not exist. If omitted, the next number is allocated."),
    files: List[models.projects.ProjFile] = Body([]),
):
    """Create a new project version."""
    return await models.projects.post_projects_version(credentials, name, ver, files)


@router.patch("/{name}/v/{ver}", response_model=models.common.PatchResponse, operation_id="project_ver_update",
              summary="Update project version.")
async def patch_project_version(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/projects/{name}/v/{ver}")),
    name: str = Path(...),
    ver: int = Path(...),
    patch: models.projects.ProjectVersionPatchBody = Body(...),
):
    """Change a project version if conditions are met."""
    return await models.projects.patch_project_version(credentials, name, ver, patch)
