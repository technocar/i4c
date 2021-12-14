# -*- coding: utf-8 -*-
from textwrap import dedent
from typing import List
from common import I4cBaseModel, DatabaseConnection
from common.cmp_list import cmp_list
from models import CommonStatusEnum

path_list = []


class Priv(I4cBaseModel):
    endpoint: str
    features: List[str]


class RoleIn(I4cBaseModel):
    subroles: List[str]
    privs: List[Priv]
    status: CommonStatusEnum


class Role(RoleIn):
    name: str


async def get_roles(credentials, name=None, *, active_only=True, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        res = []
        sql = dedent("""\
                select 
                  r.name,
                  r."status",
                  coalesce(rs.subroles, array[]::varchar[]) subroles,
                  rg.endpoint,
                  rg.features
                from "role" r
                left join (select
                        rs.role, array_agg(rs.subrole) subroles
                      from role_subrole rs
                      group by rs.role
                     ) rs on rs.role = r.name
                left join role_grant rg on rg.role = r.name
                where True 
                  <filter>
                order by r.name
            """)
        params = []
        filters = ""
        if active_only:
            filters += """and r."status" = 'active'"""
        if name is not None:
            params.append(name)
            filters += f"and r.name = ${len(params)}"
        sql = sql.replace("<filter>", filters)
        d = await conn.fetch(sql, *params)
        current_role = None
        for r in d:
            if current_role is None or (r[0] != current_role.name):
                current_role = Role(name=r["name"], status=r["status"], subroles=r["subroles"], privs=[])
                res.append(current_role)
            if r["endpoint"] is not None:
                current_role.privs.append(Priv(endpoint=r["endpoint"], features=r["features"]))
        return res


async def get_priv(credentials):
    return [Priv(endpoint=p.path, features=p.features) for p in path_list]


async def role_put(credentials, name, role: RoleIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            old = await get_roles(credentials, name, active_only=False, pconn=conn)
            if len(old) == 0:
                sql_insert = """insert into "role" (name, "status") values ($1, $2)"""
                await conn.fetchrow(sql_insert, name, role.status)
                old = Role(
                        name=name,
                        status=role.status,
                        subroles=[],
                        privs=[]
                        )
            else:
                old = old[0]
                sql_update = """update "role" set "status" = $2 where name = $1"""
                await conn.execute(sql_update, name, role.status)

            sub = cmp_list(old.subroles, role.subroles)
            for c in sub.delete:
                sql_del = "delete from role_subrole where role = $1 and subrole = $2"
                await conn.execute(sql_del, name, c)
            for c in sub.insert:
                sql_ins = "insert into role_subrole (role, subrole) values ($1, $2)"
                await conn.execute(sql_ins, name, c)

            privs = cmp_list(old.privs, role.privs, key=lambda x:x.endpoint)
            for c in privs.delete:
                sql_del = "delete from role_grant where role = $1 and endpoint = $2"
                await conn.execute(sql_del, name, c.endpoint)
            for c in privs.insert:
                sql_ins = "insert into role_grant (role, endpoint, features) values ($1, $2, $3)"
                await conn.execute(sql_ins, name, c.endpoint, c.features)
            for c in privs.update:
                sql_ins = "update role_grant set features = $3 where role = $1 and endpoint = $2"
                await conn.execute(sql_ins, name, c[1].endpoint, c[1].features)

            new_alarm = await get_roles(credentials, name, active_only=False, pconn=conn)
            return new_alarm[0]
