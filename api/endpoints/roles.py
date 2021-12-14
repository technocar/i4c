from typing import List, Optional
from fastapi import Query, Depends, Path, HTTPException, Body
from fastapi.security import HTTPBasicCredentials
import models.roles
from I4cAPI import I4cApiRouter
import common

router = I4cApiRouter(include_path="/roles")


@router.get("", response_model=List[models.roles.Role], x_properties=dict(object="roles", action="list"))
async def get_roles(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles")),
    active_only: Optional[bool] = Query(True)
):
    return await models.roles.get_roles(credentials, active_only=active_only)


@router.get("/{name}", response_model=models.roles.Role, x_properties=dict(object="roles", action="get"))
async def get_role(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles/{name}")),
    name: str = Path(...)
):
    res = await models.roles.get_roles(credentials, name, active_only=False)
    if res is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res[0]


@router.put("/{name}", response_model=models.roles.Role, x_properties=dict(object="roles", action="set"))
async def alarmdef_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/roles/{name}")),
    name: str = Path(...),
    role: models.roles.RoleIn = Body(...),
):
    return await models.roles.role_put(credentials, name, role)
