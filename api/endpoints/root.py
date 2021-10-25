from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials
import common
import models.users

router = APIRouter()


@router.get("/login", response_model=models.users.UserResponse)
async def login(
        credentials: HTTPBasicCredentials = Depends(common.security_checker())):
    "Get user info based on login name"
    return await models.users.login(credentials)
