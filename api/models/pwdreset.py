# -*- coding: utf-8 -*-
import base64
import secrets
from textwrap import dedent
from pydantic import Field
import common
import models.users
from common import I4cBaseModel, DatabaseConnection
from common.exceptions import I4cClientError


class LoginName(I4cBaseModel):
    loginname: str


async def init(loginname):
    async with DatabaseConnection() as conn:
        sql_check = """select * from "user" where login_name = $1"""
        cdb = await conn.fetchrow(sql_check, loginname)
        if not cdb:
            raise I4cClientError("Unknown login name")
        if cdb["email"] is None:
            raise I4cClientError("No registered email address for login name")

        token = secrets.token_bytes(18)
        token = base64.urlsafe_b64encode(token).decode('ascii')
        sql_update = dedent("""\
            update "user"
            set 
              pwd_reset_token = $2,
              pwd_reset_token_status = 'outbox',
              pwd_reset_token_created = now()                            
            where 
              login_name = $1
            """)
        await conn.execute(sql_update, loginname, token)


class SetPassParams(I4cBaseModel):
    """Password reset data."""
    loginname: str = Field(..., title="Login name.")
    token: str = Field(..., title="Password reset token.")
    password: str = Field(..., title="New password.")


async def setpass(loginname, token, password, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql = dedent("""\
                select *
                from "user"
                where 
                  login_name = $1
                  and pwd_reset_token = $2
                  and (now() - pwd_reset_token_created < '30 min'::interval)
                """)
            db_user = await conn.fetchrow(sql, loginname, token)
            if not db_user:
                raise I4cClientError("Authentication failed")

            sql_update = dedent("""\
                update "user"
                set 
                  password_verifier = $2,
                  pwd_reset_token = null,
                  pwd_reset_token_status = null,
                  pwd_reset_token_created = null                                              
                where 
                  login_name = $1
                """)
            new_password_verifier = common.create_password(password)
            await conn.execute(sql_update, loginname, new_password_verifier)

            return await models.users.get_user(login_name=loginname, with_privs=True)


class PwdresetOutboxItem(I4cBaseModel):
    """Password reset to be sent."""
    token: str = Field(..., title="Password reset token.")
    loginname: str = Field(..., title="Login name.")
    email: str = Field(..., title="User's email.")


async def get_outbox_list(credentials):
    async with DatabaseConnection() as conn:
        sql = dedent("""\
                select
                  pwd_reset_token as token,
                  login_name as loginname,
                  email
                from "user"
                where 
                  pwd_reset_token is not null
                  and pwd_reset_token_status = 'outbox'
                  and (now() - pwd_reset_token_created < '30 min'::interval)
                """)
        return await conn.fetch(sql)


async def set_outbox_status(credentials, loginname, new_status):
    async with DatabaseConnection() as conn:
        sql_update = dedent("""\
            update "user"
            set 
              pwd_reset_token_status = $2
            where 
              login_name = $1
              and pwd_reset_token_status = 'outbox'
            """)
        await conn.execute(sql_update, loginname, new_status)
