from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBasicCredentials
import models
import common

router = APIRouter()


@router.get("/snapshot/{cell}", response_model=models.MazakSnapshot)
def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: str = Query(..., title="Name of the devide", description="mill|lathe|gom|robot|auto")
) -> Any:
    s = models.MazakSnapshot()
    s.field1 = device
    return s
