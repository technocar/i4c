from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
import common
import models.batch
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/batch")


@router.get("", response_model=List[models.batch.BatchListItem], operation_id="batch_list", summary="List batches.")
async def batch_list(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/batch")),
        project: Optional[str] = Query(None, title="Belongs to project."),
        status: Optional[List[models.batch.BatchStatus]] = Query(None, title="Status.")):
    """Get a list of batches."""
    return await models.batch.batch_list(credentials, project, status)


@router.put("/{id}", response_model=models.batch.Batch, operation_id="batch_set", summary="Create or update batch.")
async def batch_put(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/batch/{id}")),
    id: str = Path(...),
    batch: models.batch.BatchIn = Body(...),
):
    """Create or update batch definition."""
    return await models.batch.batch_put(credentials, id, batch)
