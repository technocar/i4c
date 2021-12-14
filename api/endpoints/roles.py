from typing import List

from fastapi import Query, Depends, Path, HTTPException
from fastapi.security import HTTPBasicCredentials

import models.roles
from I4cAPI import I4cApiRouter
import common

router = I4cApiRouter(include_path="/roles")


@router.get("", response_model=List[models.roles.Role], x_properties=dict(object="roles", action="list"))
async def get_roles(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles")),
):
    return await models.roles.get_roles(credentials)


@router.get("/{name}", response_model=models.roles.Role, x_properties=dict(object="roles", action="get"))
async def get_roles(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles/{name}")),
    name: str = Path(...)
):
    res = await models.roles.get_roles(credentials, name)
    if res is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res[0]
