from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, HTTPException
from fastapi.security import HTTPBasicCredentials
import models.projects
import common
from I4cAPI import I4cApiRouter
from models import ProjectStatusEnum

router = I4cApiRouter()


@router.get("/", response_model=List[models.projects.Project], x_properties=dict(object="projects", action="list"))
async def list_projects(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects")),
    name: Optional[str] = Query(...),
    status: Optional[ProjectStatusEnum] = Query(...),
    cre_after: Optional[datetime] = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    cre_before: Optional[datetime] = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    file: Optional[str] = Query(..., description="Full savepath of the file.")
):
    return await models.projects.get_projects(credentials, name, status, cre_after, cre_before, file)


@router.get("/{name}", response_model=models.projects.Project, x_properties=dict(object="projects", action="get"))
async def get_project(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/projects/{name}")),
    name: str = Path(...),
):
    res = await models.projects.get_projects(credentials, name)
    if len(res) > 0:
        return res[0]
    raise HTTPException(status_code=404, detail="No record found")
