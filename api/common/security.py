from typing import List, Set

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
from .auth import authenticate

basic_security = HTTPBasic()


class CredentialsAndFeatures(HTTPBasicCredentials):
    user_id: str
    info_features: Set[str]


class security_checker:
    """ security_checker class, it calls authenticate to check if caller is authenticated and/or authorized

    sample usage 1:
            async def xy(
                    credentials: HTTPBasicCredentials = Depends(common.security_checker())

    sample usage 2:
            async def xy(
                    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/xy"))

    sample usage 3:
            async def xy(
                    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/xy",["xy call spec"]))

    sample usage 3:
            async def xy(
                    credentials: CredentialsAndFeatures = Depends(common.security_checker("get/xy",["xy call spec"],["xy call spec2"]))

    """
    def __init__(self, endpoint=None, need_features=None, ask_features=None):
        self.endpoint = endpoint
        self.need_features = need_features
        self.ask_features = ask_features

    async def __call__(self, credentials: HTTPBasicCredentials = Depends(basic_security)):
        uid, info_features = await authenticate(credentials.username, credentials.password,
                                                self.endpoint, self.need_features, self.ask_features)
        if not uid:
            raise HTTPException(
                # when we return HTTP_401_UNAUTHORIZED then blowser pops up login dialog
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Basic"})

        return CredentialsAndFeatures(user_id=uid, username=credentials.username, password=credentials.password, info_features=info_features)
