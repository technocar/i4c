from typing import List
from fastapi import HTTPException
from textwrap import dedent
from common import DatabaseConnection
from models import DataPoint


async def put_log_write(credentials, datapoints: List[DataPoint], *, pconn=None):
    try:
        sql = dedent("""\
                     insert into public.log
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
                       DO NOTHING""")

        async with DatabaseConnection(pconn) as conn:
            async with conn.transaction():
                for d in datapoints:
                    await conn.execute(sql,
                                       d.device, d.instance, d.timestamp,
                                       d.sequence, d.data_id, d.value_num,
                                       d.value_text, d.value_extra, d.value_add)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")
