from fastapi import Depends
from fastapi.security import HTTPBasicCredentials
import common
import models.users
from I4cAPI import I4cApiRouter

router = I4cApiRouter()


@router.get("/login", response_model=models.users.UserResponse, tags=["log"], x_properties=dict(object="user", action="login"))
async def login(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/login"))):
    "Get user info based on login name"
    return await models.users.login(credentials)
