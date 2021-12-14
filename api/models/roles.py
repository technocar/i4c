# -*- coding: utf-8 -*-
from textwrap import dedent
from typing import List
from common import I4cBaseModel, DatabaseConnection

path_list = []


class Priv(I4cBaseModel):
    endpoint: str
    features: List[str]


class RoleIn(I4cBaseModel):
    subroles: List[str]
    privs: List[Priv]


class Role(RoleIn):
    name: str


async def get_roles(credentials, name=None):
    async with DatabaseConnection() as conn:
        res = []
        sql = dedent("""\
                select 
                  r.name,
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
                where 
                  r."status" = 'active'
                  <filter>
                order by r.name
            """)
        params = []
        filters = ""
        if name is not None:
            filters = "and r.name = $1"
            params.append(name)
        sql = sql.replace("<filter>", filters)
        d = await conn.fetch(sql, *params)
        current_role = None
        for r in d:
            if current_role is None or (r[0] != current_role.name):
                current_role = Role(name=r[0], subroles=r[1], privs=[])
                res.append(current_role)
            if r[2] is not None:
                current_role.privs.append(Priv(endpoint=r[2], features=r[3]))
        return res


async def get_priv(credentials):
    return [Priv(endpoint=p.path, features=p.features) for p in path_list]
