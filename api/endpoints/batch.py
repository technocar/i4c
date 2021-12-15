from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
import common
import models.batch
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/batch")


@router.get("", response_model=List[models.batch.ListItem], x_properties=dict(object="batch", action="list"))
async def batch_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/batch")),
        project: Optional[str] = Query(None),
        status: Optional[List[models.batch.BatchStatus]] = Query(None)):
    return await models.batch.batch_list(credentials, project, status)


@router.put("/{id}", response_model=models.batch.Batch, x_properties=dict(object="batch", action="set"))
async def batch_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/batch/{id}")),
    id: str = Path(...),
    batch: models.batch.BatchIn = Body(...),
):
    """Create or update batch definition."""
    return await models.batch.batch_put(credentials, id, batch)
