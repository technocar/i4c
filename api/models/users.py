from textwrap import dedent

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Optional, List

from common import DatabaseConnection
from models import UserStatusEnum


class UserData(BaseModel):
    """Represents data fields of a real person or automated account. Setting the password is not possible here, please use PATCH"""
    name: str = Field(..., title="User's name")
    roles: List[str] = Field(..., title="Assigned roles")
    status: UserStatusEnum = Field(...)
    login_name: str = Field(..., title="Login name")
    pub_key: Optional[str] = Field(None, nullable=True, title="Public key for signed requests")


class User(UserData):
    """Represents a real person or automated account."""
    id: str = Field(..., title="User's identifier")
    roles_eff: List[str] = Field(..., title="All roles assigned directly or indirectly")


class UserResponse(BaseModel):
    """Single user response"""
    user: User


class UserListResponse(BaseModel):
    """Multi user response"""
    users: List[User]


def user_from_row(row):
    d = dict(row)
    d.pop("password_verifier", None)
    return d


async def login(credentials: HTTPBasicCredentials, *, pconn=None):
    sql = dedent("""\
            select *
            from public."user" u
            where 
              u."login_name" = $1
          """)
    async with DatabaseConnection(pconn) as conn:
        res = await conn.fetchrow(sql, credentials.username)
        if not res:
            raise HTTPException(status_code=500, detail="User record not found")
        res = user_from_row(res)
        # todo 1: *****
        res["roles"] = []
        res["roles_eff"] = []
        return {"user": res}

