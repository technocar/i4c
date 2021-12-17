from typing import List, Optional
from fastapi import Query, Depends, Path, Body
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBasicCredentials
import models.users
from I4cAPI import I4cApiRouter
import common
import models.common
from common import CredentialsAndFeatures
from common.exceptions import I4cClientNotFound

router = I4cApiRouter(include_path="/users")


@router.get("/create_password", response_class=PlainTextResponse, include_in_schema=False)
async def create_password(password: str = Query(...)):
    return common.create_password(password)


@router.get("", response_model=List[models.users.User], x_properties=dict(object="users", action="list"))
async def get_users(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/users")),
    active_only: Optional[bool] = Query(True)
):
    return await models.users.get_users(credentials, active_only=active_only)


@router.get("/{id}", response_model=models.users.User, x_properties=dict(object="users", action="get"))
async def get_user(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/users/{id}")),
    id: str = Path(...)
):
    res = await models.users.get_user(user_id=id)
    if res is None:
        raise I4cClientNotFound("User record not found")
    return res


@router.put("/{id}", response_model=models.users.User, x_properties=dict(object="users", action="set"),
            features=['modify others', 'modify role'])
async def user_put(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("put/users/{id}", ask_features=['modify others', 'modify role'])),
    id: str = Path(...),
    user: models.users.UserIn = Body(...),
):
    return await models.users.user_put(credentials, id, user)


@router.patch("/{id}", response_model=models.common.PatchResponse,
              x_properties=dict(object="users", action="patch"), features=['modify others'])
async def user_patch(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("patch/users/{id}", ask_features=['modify others'])),
    id: str = Path(...),
    patch: models.users.UserPatchBody = Body(...),
):
    return await models.users.user_patch(credentials, id, patch)
