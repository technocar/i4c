from typing import List
from textwrap import dedent
from common import DatabaseConnection
from common.db_tools import dict2asyncpg_param
from common.exceptions import I4cClientError
from models.log import DataPointLog


async def check_data_id(conn, device, timestamp, sequence, data_id):
    sql = dedent("""\
        select data_id from log
        where 
          device = $1 
          and "timestamp" = $2
          and sequence = $3
        """)
    r = await conn.fetchrow(sql, device, timestamp, sequence)
    if r and r[0] != data_id:
        raise I4cClientError("data_id update is not allowed")


async def put_log_write(credentials, datapoints: List[DataPointLog], *, override=False, pconn=None):
    on_conflict = "DO NOTHING" if not override else """\
                   DO UPDATE SET 
                     instance = EXCLUDED.instance,
                     value_num = EXCLUDED.value_num,
                     value_text = EXCLUDED.value_text,
                     value_extra = EXCLUDED.value_extra,
                     value_aux = EXCLUDED.value_aux
                   """
    sql = dedent(f"""\
                 insert into log
                 (
                    device,
                    instance,
                    "timestamp",
                    sequence,
                    data_id,
                    value_num,
                    value_text,
                    value_extra,
                    value_aux
                   )
                   values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   ON CONFLICT (device, "timestamp", sequence)
                   {on_conflict}""")

    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction():
            for d in datapoints:
                if override:
                    await check_data_id(conn, d.device, d.timestamp,
                                   d.sequence, d.data_id)
                await conn.execute(sql,
                               d.device, d.instance, d.timestamp,
                               d.sequence, d.data_id, d.value_num,
                               d.value_text, d.value_extra, dict2asyncpg_param(d.value_add))
