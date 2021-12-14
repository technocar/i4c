from typing import List, Optional
from fastapi import Query, Depends, Path, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBasicCredentials
import models.users
from I4cAPI import I4cApiRouter
import common

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


@router.get("/{name}", response_model=models.users.User, x_properties=dict(object="users", action="get"))
async def get_user(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/users/{name}")),
    name: str = Path(...)
):
    res = await models.users.get_users(credentials, name, active_only=False)
    if res is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res[0]



