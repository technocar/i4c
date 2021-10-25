from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
from .auth import authenticate

basic_security = HTTPBasic()


class security_checker:
    def __init__(self, endpoint=None, need_features=None):
        self.endpoint = endpoint
        self.need_features = need_features

    async def __call__(self, credentials: HTTPBasicCredentials = Depends(basic_security)):
        uid, _ = await authenticate(credentials.username, credentials.password, self.endpoint, self.need_features)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"})
        return credentials
