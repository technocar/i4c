from typing import Optional, List
from fastapi import Depends, Query, Path
from fastapi.security import HTTPBasicCredentials
import models.installations
import common
from I4cAPI import I4cApiRouter
from models import ProjectVersionStatusEnum

router = I4cApiRouter()


@router.post("/{project}/{version}", response_model=models.installations.Installations, x_properties=dict(object="projects", action="list"))
async def new_installation(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/installations/{project}/{version}")),
    project: str = Path(...),
    version: str = Path(...),
    statuses: Optional[List[ProjectVersionStatusEnum]] = Query(None, description="Allowed project statuses, default [final]")
):
    return await models.installations.new_installation(credentials, project, version, statuses)
