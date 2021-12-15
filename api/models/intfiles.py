import os
from hashlib import sha384
from textwrap import dedent
from fastapi.security import HTTPBasicCredentials
from starlette.responses import FileResponse

import common
import common.db_helpers
from common import I4cBaseModel, DatabaseConnection
from common.exceptions import I4cClientError, I4cClientNotFound


class FileDetail(I4cBaseModel):
    name:str
    ver: int
    size: int
    hash: str


def get_internal_file_name(hash):
    fn = common.apicfg["internal_file"]["path"]
    return os.sep.join([fn, hash])


async def intfiles_list(credentials, name, name_mask, min_ver, max_ver, hash, *, pconn=None):
    sql = dedent("""\
                with
                    res as (
                        SELECT f.name, f.ver, f.content_hash as hash
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

    if name_mask is not None:
        sql += "and " + common.db_helpers.filter2sql(name_mask, "res.name", params)

    add_param(min_ver, "ver", operator=">=")
    add_param(max_ver, "ver", operator="<=")
    add_param(hash, "hash")
    async with DatabaseConnection(pconn) as conn:
        dres = await conn.fetch(sql, *params)
        res = []
        for r in dres:
            res.append(FileDetail(name=r["name"],
                                  ver=r["ver"],
                                  size=os.path.getsize(get_internal_file_name(r["hash"])),
                                  hash=r["hash"]))
        return res


async def intfiles_get(credentials, ver, name, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
            select content_hash
            from file_int
            where name = $1 and ver = $2
        """)
        res = await conn.fetchrow(sql, name, ver)
        if res:
            path = get_internal_file_name(res[0])
            if os.path.isfile(path):
                return FileResponse(path,
                                    filename=os.path.basename(name),
                                    media_type="application/octet-stream")
            raise I4cClientNotFound("No file found")


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
                raise I4cClientError("Internal file used in non-edit project")
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
            hash = sha384(file).digest().hex()
            if id:
                sql_update = dedent("""\
                    update file_int
                    set content_hash = $1
                    where id = $2
                """)
                await conn.execute(sql_update, hash, id)

            else:
                sql_insert = "insert into file_int (name, ver, content_hash) values ($1, $2, $3)"
                await conn.execute(sql_insert, name, ver, hash)

            fn = get_internal_file_name(hash)
            if not os.path.isfile(fn):
                with open(fn, "wb") as f:
                    f.write(file)


async def intfiles_delete(credentials, ver, name):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            id = await intfiles_check_usage(ver, name, pconn=conn)
            if id:
                # todo maybe delete file from disk. Delete only when no file with this hash are in use.
                sql_update = "delete from file_int where id = $1"
                await conn.execute(sql_update, id)
