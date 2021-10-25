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
    sql_user = dedent("""\
            select *
            from "user"
            where "user".login_name = $1
          """)

    sql_roles = dedent("""\
            select user_role.role
            from user_role 
            where user_role."user" = $1
          """)

    sql_roles_eff = dedent("""\
            with
              recursive deep_role_r as
                (select distinct "name" as toprole, "name" as midrole, "name" as subrole from "role"
                 union
                 select deep_role_r.toprole, role_subrole.role as midrole, role_subrole.subrole
                 from deep_role_r 
                 join role_subrole on deep_role_r."subrole" = role_subrole."role"),
              deep_role as (select distinct toprole as role, subrole from deep_role_r)
            select distinct 
              deep_role.subrole as "role"
            from user_role 
            join deep_role on deep_role.role = user_role."role"
            join role_grant on deep_role.subrole = role_grant."role"
            where user_role."user" = $1
          """)
    async with DatabaseConnection(pconn) as conn:
        db_user = await conn.fetchrow(sql_user, credentials.username)
        if not db_user:
            raise HTTPException(status_code=500, detail="User record not found")
        res = user_from_row(db_user)

        res_roles = []
        db_roles = await conn.fetchrow(sql_roles, res["id"])
        for r in db_roles:
            res_roles.append(r)
        res["roles"] = res_roles

        res_roles_eff = []
        db_roles_eff = await conn.fetchrow(sql_roles_eff, res["id"])
        for r in db_roles_eff:
            res_roles_eff.append(r)
        res["roles_eff"] = res_roles_eff

        return {"user": res}
