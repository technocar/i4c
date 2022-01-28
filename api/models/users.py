from textwrap import dedent
from asyncpg import ForeignKeyViolationError, UniqueViolationError
from fastapi.security import HTTPBasicCredentials
from pydantic import Field, root_validator
from typing import Optional, List
import common
from common import I4cBaseModel, DatabaseConnection, CredentialsAndFeatures
from common.cmp_list import cmp_list
import common.tools
from common.exceptions import I4cClientError
from models import UserStatusEnum
from models.common import PatchResponse
from models.roles import Priv


class UserData(I4cBaseModel):
    """Core fields of a real person or automated account."""
    name: str = Field(..., title="User's name")
    roles: List[str] = Field([], title="Assigned roles")
    status: UserStatusEnum = Field("active")
    login_name: Optional[str] = Field(None, title="Login name")
    public_key: Optional[str] = Field(None, nullable=True, title="Public key for signed requests")
    customer: Optional[str] = Field(None, nullable=True)
    email: Optional[str] = Field(None, nullable=True)


class User(UserData):
    """Real person or automated account."""
    id: str = Field(..., title="User's identifier")
    roles_eff: List[str] = Field(..., title="All roles assigned directly or indirectly")


class UserWithPrivs(User):
    """Real person or automated account with privileges."""
    privs: List[Priv]


class UserPatchChange(I4cBaseModel):
    """Change in a user update."""
    password: Optional[str] = Field(None, title="Set password.")
    del_password: Optional[bool] = Field(None, title="If set, removes the password.")
    public_key: Optional[str] = Field(None, title="Public key.")
    del_public_key: Optional[bool] = Field(None, title="If set, remove the public key.")
    status: Optional[UserStatusEnum] = Field(None, title="Set status.")
    customer: Optional[str] = Field(None, nullable=True, title="Set customer.")
    email: Optional[str] = Field(None, nullable=True, title="Set email.")

    @root_validator
    def check_exclusive(cls, values):
        common.tools.check_exclusive(values, ['password', 'del_password'])
        common.tools.check_exclusive(values, ['public_key', 'del_public_key'])
        return values

    def is_empty(self):
        return ( self.password is None
                 and (self.del_password is None or not self.del_password)
                 and self.public_key is None
                 and (self.del_public_key is None or not self.del_public_key)
                 and self.status is None
                 and self.customer is None
                 and self.email is None)


class UserPatchBody(I4cBaseModel):
    """Update to a user."""
    change: UserPatchChange


def user_from_row(row):
    d = dict(row)
    d.pop("password_verifier", None)
    d.pop("pwd_reset_token", None)
    return d


async def get_user(*, user_id=None, login_name=None, active_roles_only=True, with_privs=False, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql_user = dedent("""\
                select *
                from "user" u
                where True
                <filter>
              """)
        params = []
        filters = ""
        if user_id is not None:
            params.append(user_id)
            filters += f"and u.id = ${len(params)}"
        if login_name is not None:
            params.append(login_name)
            filters += f"and u.login_name = ${len(params)}"
        if len(params) == 0:
            raise I4cClientError("user_id or login_name should be supplied")
        sql_user = sql_user.replace("<filter>", filters)
        del filters
        db_user = await conn.fetchrow(sql_user, *params)
        if not db_user:
            return None
        res = user_from_row(db_user)

        sql_roles = dedent("""\
                select ur.role
                from user_role ur
                join "role" r on r.name = ur.role
                where ur."user" = $1
                <filter>
              """)
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
        res_roles_eff = []
        privs = []
        filters = ""
        if active_roles_only:
            filters = """and r."status" = 'active'"""
        sql_roles_eff = sql_roles_eff.replace("<filter>", filters)
        del filters
        db_roles_eff = await conn.fetch(sql_roles_eff, res["id"])
        for r in db_roles_eff:
            res_roles_eff.append(r[0])
            if with_privs:
                sql = """select endpoint, features from role_grant where role = $1"""
                db_privs = await conn.fetch(sql, r[0])
                privs.extend([Priv(endpoint=r["endpoint"], features=r["features"]) for r in db_privs])
        res["roles_eff"] = res_roles_eff
        if with_privs:
            res["privs"] = privs
            return UserWithPrivs(**res)
        else:
            return User(**res)


async def login(credentials: HTTPBasicCredentials, *, pconn=None):
    res = await get_user(login_name=credentials.username, with_privs=True, pconn=pconn)
    return res


async def customer_list(credentials: HTTPBasicCredentials, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = """select distinct "customer" from "user" where "customer" is not null order by 1"""
        res = await conn.fetch(sql)
        res = [r[0] for r in res]
        return res


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


async def user_put(credentials: CredentialsAndFeatures, id, user: UserData, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            if id != credentials.user_id:
                if 'modify others' not in credentials.info_features:
                    raise I4cClientError("Unable to modify other user's data")

            old = await get_user(user_id=id, active_roles_only=False, pconn=conn)
            if not old:
                old_roles = []
                sql = dedent("""\
                    insert into "user"
                        (id, name, "status", login_name, customer, email, public_key)
                    values
                        ($1, $2, $3,         $4, $5, $6,                  $7 )""")
            else:
                old_roles = old.roles
                sql = dedent("""\
                        update "user"
                        set
                            name = $2, "status" = $3, login_name = $4, customer = $5, email = $6, public_key = $7
                        where id = $1""")
            try:
                await conn.fetchrow(sql, id, user.name, user.status, user.login_name,
                                    user.customer, user.email, user.public_key)
            except UniqueViolationError as e:
                if hasattr(e, 'constraint_name'):
                    if e.constraint_name == 'uq_user_login':
                        raise I4cClientError("Login name must be unique.")
                raise e

            sub = cmp_list(old_roles, user.roles)
            if len(sub.delete) > 0 or len(sub.insert) > 0:
                if 'modify role' not in credentials.info_features:
                    raise I4cClientError("You are not allowed to modify users' roles")
            for c in sub.delete:
                sql_del = """delete from user_role where "user" = $1 and role = $2"""
                await conn.execute(sql_del, id, c)
            for c in sub.insert:
                try:
                    sql_ins = """insert into user_role ("user", role) values ($1, $2)"""
                    await conn.execute(sql_ins, id, c)
                except ForeignKeyViolationError:
                    raise I4cClientError(f"invalid role={c}")

            return await get_user(user_id=id, pconn=conn)


async def user_patch(credentials: CredentialsAndFeatures, id, patch:UserPatchBody, *, pconn=None):
    if id != credentials.user_id:
        if 'modify others' not in credentials.info_features:
            raise I4cClientError("Unable to modify other user's data")

    if patch.change.is_empty():
        return PatchResponse(changed=True)

    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
                  update "user"
                  set
                    <fields>
                  where id = $1
                  """)
        fields = []
        params = [id]
        if patch.change.password is not None:
            params.append(common.create_password(patch.change.password))
            fields.append(f"password_verifier = ${len(params)}")
        if patch.change.del_password:
            fields.append(f"password_verifier = null")
        if patch.change.public_key is not None:
            params.append(patch.change.public_key)
            fields.append(f"public_key = ${len(params)}")
        if patch.change.del_public_key:
            fields.append(f"public_key = null")
        if patch.change.status is not None:
            params.append(patch.change.status)
            fields.append(f""""status" = ${len(params)}""")
        if patch.change.customer is not None:
            params.append(patch.change.customer)
            fields.append(f""""customer" = ${len(params)}""")
        if patch.change.email is not None:
            params.append(patch.change.email)
            fields.append(f""""email" = ${len(params)}""")
        sql = sql.replace("<fields>", ',\n'.join(fields))
        await conn.execute(sql, *params)
        return PatchResponse(changed=True)
