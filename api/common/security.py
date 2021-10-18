from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status

basic_security = HTTPBasic()

async def security_checker(credentials: HTTPBasicCredentials = Depends(basic_security)):
    if credentials.username != 'aaa':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Basic"})
    return credentials
