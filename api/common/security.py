from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
from .auth import authenticate
from .db_pool import DatabaseConnection

basic_security = HTTPBasic()


async def security_checker(credentials: HTTPBasicCredentials = Depends(basic_security)):
    uid, _ = await authenticate(credentials.username, credentials.password)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Basic"})
    return credentials
