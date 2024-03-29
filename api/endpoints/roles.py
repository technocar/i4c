from typing import List, Optional
from fastapi import Query, Depends, Path, Body
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
import models.roles
from I4cAPI import I4cApiRouter
import common
from common.exceptions import I4cClientNotFound

router = I4cApiRouter(include_path="/roles")


@router.get("", response_model=List[models.roles.Role], operation_id="role_list", summary="List roles.")
async def get_roles(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles")),
    active_only: Optional[bool] = Query(True)
):
    """List roles."""
    return await models.roles.get_roles(credentials, active_only=active_only)


@router.get("/{name}", response_model=models.roles.Role, operation_id="role_get", summary="Retrieve role.")
async def get_role(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles/{name}")),
    name: str = Path(...)
):
    """Get a role."""
    res = await models.roles.get_roles(credentials, name, active_only=False)
    if not res:
        raise I4cClientNotFound("No record found")
    return res[0]


@router.put("/{name}", response_model=models.roles.Role, operation_id="role_set", summary="Create or update role.")
async def role_put(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/roles/{name}")),
    name: str = Path(...),
    role: models.roles.RoleIn = Body(...),
):
    """Create or update a role."""
    return await models.roles.role_put(credentials, name, role)
