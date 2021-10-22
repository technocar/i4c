from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
from .auth import authenticate

basic_security = HTTPBasic()


async def security_checker(credentials: HTTPBasicCredentials = Depends(basic_security)):
    await authenticate(credentials.username, credentials.password)
    return credentials
