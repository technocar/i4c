from base64 import b64encode
from hashlib import sha384
from textwrap import dedent
from typing import Union, List
from fastapi import UploadFile, HTTPException
from fastapi.security import HTTPBasicCredentials
from common import I4cBaseModel, DatabaseConnection


class FileDetail(I4cBaseModel):
    name:str
    ver: int
    size: int
    hash: str


async def intfiles_list(credentials, name, min_ver, max_ver, hash, *, pconn=None):
    sql = dedent("""\
                with
                    res as (
                        SELECT f.name, f.ver, length(f.content) as size, f.content_hash as hash
                        from file_int f
                    )
                select * 
                from res
                where True
          """)
    params = []

    def add_param(value, col_name, *, operator="=", param_type=None):
        nonlocal sql
        nonlocal params
        if value is not None:
            params.append(value)
            sp = f"::{param_type}" if param_type else ""
            sql += f"and res.{col_name} {operator} ${len(params)}{sp}\n"

    add_param(name, "name")
    add_param(min_ver, "ver", operator=">=")
    add_param(max_ver, "ver", operator="<=")
    add_param(hash, "hash")
    async with DatabaseConnection(pconn) as conn:
        return await conn.fetch(sql, *params)


async def intfiles_get(credentials, ver, path):
    # todo 1: **********
    return r'c:\Gy\SQL\truncate_log.ssr'


async def intfiles_check_usage(ver: int, name: str, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
            select id
            from file_int
            where name = $1 and ver = $2
        """)
        idr = await conn.fetchrow(sql, name, ver)
        id = idr[0] if idr else None
        if id:
            sql_check_usage = dedent("""\
                select *
                from project_file pf
                join project_version pv on pv.id = pf.project_ver
                where pf.file_int = $1 and pv.status != 'edit'                
            """)
            dc = await conn.fetch(sql_check_usage, id)
            if dc:
                raise HTTPException(status_code=400, detail="Internal file used in non-edit project")
        return id



async def intfiles_put(
    credentials: HTTPBasicCredentials,
    ver: int,
    name: str,
    file: bytes
):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            id = await intfiles_check_usage(ver, name, pconn=conn)
            hash = b64encode(sha384(file).digest()).decode('utf-8')
            if id:
                sql_update = dedent("""\
                    update file_int
                    set content_hash = $1,
                        content = $2
                    where id = $3
                """)
                await conn.execute(sql_update, hash, file, id)
            else:
                sql_insert = "insert into file_int (name, ver, content_hash, content) values ($1, $2, $3, $4)"
                await conn.execute(sql_insert, name, ver, hash, file)


async def intfiles_delete(credentials, ver, path):
    # todo 1: **********
    pass
