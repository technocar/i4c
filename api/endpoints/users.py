from typing import List, Optional
from fastapi import Query, Depends, Path, Body
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
import models.users
from I4cAPI import I4cApiRouter
import common
import models.common
from common import CredentialsAndFeatures
from common.exceptions import I4cClientNotFound

router = I4cApiRouter(include_path="/users")


@router.get("/create_password", response_class=PlainTextResponse, include_in_schema=False,
            operation_id="user_scramble_password", summary="Scramble password")
async def create_password(
        request: Request,
        password: str = Query(...)):
    """Test endpoint, create a password hash of a password."""
    return common.create_password(password)


@router.get("", response_model=List[models.users.User], operation_id="user_list", summary="List users.")
async def get_users(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/users")),
    active_only: Optional[bool] = Query(True)
):
    """List users."""
    return await models.users.get_users(credentials, active_only=active_only)


@router.get("/{id}", response_model=models.users.User, operation_id="user_get", summary="Retrieve user.")
async def get_user(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/users/{id}")),
    id: str = Path(...)
):
    """Get a user."""
    res = await models.users.get_user(user_id=id)
    if res is None:
        raise I4cClientNotFound("User record not found")
    return res


@router.put("/{id}", response_model=models.users.User, operation_id="user_set",
            summary="Create or update user.", features=['modify others', 'modify role'])
async def user_put(
    request: Request,
    credentials: CredentialsAndFeatures = Depends(common.security_checker("put/users/{id}", ask_features=['modify others', 'modify role'])),
    id: str = Path(...),
    user: models.users.UserData = Body(...),
):
    """Create or update a user."""
    return await models.users.user_put(credentials, id, user)


@router.patch("/{id}", response_model=models.common.PatchResponse, operation_id="user_update",
              summary="Update user.", features=['modify others'])
async def user_patch(
    request: Request,
    credentials: CredentialsAndFeatures = Depends(common.security_checker("patch/users/{id}", ask_features=['modify others'])),
    id: str = Path(...),
    patch: models.users.UserPatchBody = Body(...),
):
    """Apply changes to a user."""
    return await models.users.user_patch(credentials, id, patch)
