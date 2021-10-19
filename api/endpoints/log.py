from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBasicCredentials
import models
import common

router = APIRouter()


@router.get("/snapshot/{cell}", response_model=models.MazakSnapshot)
async def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker),
    cell: int = Query(..., title="cell id"),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: str = Query(..., title="Name of the devide", description="mill|lathe|gom|robot|auto")
):
    return await models.get_snapshot(credentials, cell, ts, device)
