from fastapi import HTTPException
from textwrap import dedent
from common import DatabaseConnection
from models.log import DataPointKey


async def delete_log(credentials, datapoint: DataPointKey, *, pconn=None):
    try:
        sql = dedent("""\
                     delete from public.log
                     where 
                        device = $1
                        and "timestamp" = $2
                        and sequence = $3
                        and data_id = $4
                    """)

        async with DatabaseConnection(pconn) as conn:
            await conn.execute(sql,
                               datapoint.device, datapoint.timestamp,
                               datapoint.sequence, datapoint.data_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Sql error: {e}")
