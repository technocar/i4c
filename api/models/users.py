from textwrap import dedent

from asyncpg import ForeignKeyViolationError
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import Field
from typing import Optional, List

import common
from common import I4cBaseModel, DatabaseConnection
from common.cmp_list import cmp_list
from models import UserStatusEnum
from starlette import status


class UserData(I4cBaseModel):
    """Represents data fields of a real person or automated account"""
    name: str = Field(..., title="User's name")
    roles: List[str] = Field(..., title="Assigned roles")
    status: UserStatusEnum = Field(...)
    login_name: str = Field(..., title="Login name")
    public_key: Optional[str] = Field(None, nullable=True, title="Public key for signed requests")
    customer: Optional[str] = Field(None, nullable=True)


class UserIn(UserData):
    password: str


class User(UserData):
    """Represents a real person or automated account."""
    id: str = Field(..., title="User's identifier")
    roles_eff: List[str] = Field(..., title="All roles assigned directly or indirectly")


class UserResponse(I4cBaseModel):
    """Single user response"""
    user: User


def user_from_row(row):
    d = dict(row)
    d.pop("password_verifier", None)
    d.pop("pwd_reset_token", None)
    return d


async def get_user(*, user_id=None, login_name=None, active_roles_only=True, pconn=None):
    sql_user = dedent("""\
            select *
            from "user" u
            where True
            <filter>
          """)

    sql_roles = dedent("""\
            select ur.role
            from user_role ur
            join "role" r on r.name = ur.role 
            where ur."user" = $1
            <filter>
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
            join "role" r on r.name = deep_role.subrole
            where user_role."user" = $1
            <filter>
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        filters = ""
        if user_id is not None:
            params.append(user_id)
            filters += f"and u.id = ${len(params)}"
        if login_name is not None:
            params.append(login_name)
            filters += f"and u.login_name = ${len(params)}"
        if len(params) == 0:
            raise HTTPException(status_code=400, detail="user_id or login_name should be supplied")
        sql_user = sql_user.replace("<filter>", filters)
        del filters
        db_user = await conn.fetchrow(sql_user, *params)
        if not db_user:
            return None
        res = user_from_row(db_user)

        res_roles = []
        filters = ""
        if active_roles_only:
            filters = """and r."status" = 'active'"""
        sql_roles = sql_roles.replace("<filter>", filters)
        del filters
        db_roles = await conn.fetch(sql_roles, res["id"])
        for r in db_roles:
            res_roles.append(r[0])
        res["roles"] = res_roles

        res_roles_eff = []
        filters = ""
        if active_roles_only:
            filters = """and r."status" = 'active'"""
        sql_roles_eff = sql_roles_eff.replace("<filter>", filters)
        del filters
        db_roles_eff = await conn.fetch(sql_roles_eff, res["id"])
        for r in db_roles_eff:
            res_roles_eff.append(r[0])
        res["roles_eff"] = res_roles_eff

        return User(**res)


async def login(credentials: HTTPBasicCredentials, *, pconn=None):
    res = await get_user(login_name=credentials.username)
    # todo 5: this should be just: return res
    return {"user": res}


async def resetpwd(loginname, token, password, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql = dedent("""\
                select *
                from "user"
                where 
                  login_name = $1
                  and pwd_reset_token = $2
                """)
            db_user = await conn.fetchrow(sql, loginname, token)
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Authentication failed")

            sql_update = dedent("""\
                update "user"
                set 
                  password_verifier = $2,
                  pwd_reset_token = null                            
                where 
                  login_name = $1
                """)
            new_password_verifier = common.create_password(password)
            await conn.execute(sql_update, loginname, new_password_verifier)


async def get_users(credentials, login_name=None, *, active_only=True, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
                select 
                  u.id
                from "user" u
                where True 
                  <filter>
                """)
        params = []
        filters = ""
        if active_only:
            filters += """and u."status" = 'active'"""
        if login_name is not None:
            filters += "and u.login_name = $1"
            params.append(login_name)
        sql = sql.replace("<filter>", filters)
        d = await conn.fetch(sql, *params)
        res = [await get_user(user_id=r[0]) for r in d]
        return res


async def user_put(credentials, id, user: UserIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            old = await get_user(user_id=id, active_roles_only=False, pconn=conn)
            if not old:
                old_roles = []
                sql = """insert into "user" (id, name, "status", login_name, password_verifier, customer) 
                                     values ($1, $2, $3,         $4, $5, $6)"""
            else:
                old_roles = old.roles
                sql = """update "user" set name = $2, "status" = $3, login_name = $4, password_verifier = $5, customer = $6 where id = $1"""
            await conn.fetchrow(sql, id, user.name, user.status, user.login_name, common.create_password(user.password), user.customer)

            sub = cmp_list(old_roles, user.roles)
            for c in sub.delete:
                sql_del = """delete from user_role where "user" = $1 and role = $2"""
                await conn.execute(sql_del, id, c)
            for c in sub.insert:
                try:
                    sql_ins = """insert into user_role ("user", role) values ($1, $2)"""
                    await conn.execute(sql_ins, id, c)
                except ForeignKeyViolationError:
                    raise HTTPException(status_code=400, detail=f"invalid role={c}")

            return await get_user(user_id=id, pconn=conn)
