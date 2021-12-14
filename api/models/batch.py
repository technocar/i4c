from datetime import datetime
from textwrap import dedent
from typing import Optional

from common import I4cBaseModel, DatabaseConnection
from enum import Enum


class BatchStatus(str, Enum):
    planned = "planned"
    active = "active"
    closed = "closed"
    deleted = "deleted"


class BatchIn(I4cBaseModel):
    customer: Optional[str]
    project: str
    target_count: Optional[int]
    status: BatchStatus


class Batch(BatchIn):
    batch: str


class ListItem(Batch):
    last: Optional[datetime]


batch_list_sql = open("models\\batch_list.sql").read()


async def batch_list(credentials, project, status, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        return await conn.fetch(batch_list_sql, project, status)


async def batch_put(credentials, id, batch, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            batch_exists = await conn.fetchrow("select from batch where id = $1", id)
            if batch_exists is None:
                sql = "insert into batch (id, customer, project, target_count, \"status\") values ($1, $2, $3, $4, $5)"
            else:
                sql = "update batch set customer = $2, project = $3, target_count = $4, \"status\" = $5 where id = $1"
            await conn.execute(sql, id, batch.customer, batch.project, batch.target_count, batch.status)
            return Batch(batch=id, **batch.__dict__)
