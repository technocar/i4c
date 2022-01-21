from datetime import datetime
from typing import Optional
from pydantic import Field

from common import I4cBaseModel, DatabaseConnection
from enum import Enum

from common.db_tools import get_user_customer


class BatchStatus(str, Enum):
    planned = "planned"
    active = "active"
    closed = "closed"
    deleted = "deleted"


class BatchIn(I4cBaseModel):
    """Batch of machining operations. Input."""
    customer: Optional[str] = Field(None, title="Customer that ordered the item.")
    project: str = Field(..., title="Manufacturing program collection.")
    target_count: Optional[int] = Field(None, title="Number of items to produce.")
    status: BatchStatus = Field(..., title="Status.")


class Batch(BatchIn):
    """Batch of machining operations."""
    batch: str = Field(..., title="Batch number or code.")


class BatchListItem(Batch):
    """Batch of machining operations, with last date."""
    last: Optional[datetime] = Field(None, title="Date of the last machining.")


batch_list_sql = open("models/batch_list.sql").read()


async def batch_list(credentials, project, status, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        customer = await get_user_customer(credentials.user_id, pconn=conn)
        return await conn.fetch(batch_list_sql, project, status, customer)


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
