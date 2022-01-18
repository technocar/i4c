from textwrap import dedent
from common import DatabaseConnection
from models.log import DataPointKey


async def delete_log(credentials, datapoint: DataPointKey, *, pconn=None):
    sql = dedent("""\
                 delete from log
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
