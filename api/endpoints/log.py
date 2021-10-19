from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Path
from fastapi.security import HTTPBasicCredentials
import models
import common

router = APIRouter()


@router.get("/snapshot", response_model=models.Snapshot)
async def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: str = Query(..., title="Name of the devide", description="mill|lathe|gom|robot|auto")
):
    return await models.get_snapshot(credentials, ts, device)


@router.get("/find", response_model=models.FindResult)
async def find(
        credentials: HTTPBasicCredentials = Depends(common.security_checker),
        device: str = Query(..., title="device"),
        before: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        after: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        categ: Optional[str] = Query(None, description="“condition”, “event” or “sample”"),
        name: Optional[str] = Query(None, description="exactly one of categ or name is required"),
        val: Optional[List[str]] = Query(None),
        extra: Optional[str] = Query(None),
        rel: Optional[str] = Query(None)):
    return await models.get_find(credentials, device, before, after, categ, name, val, extra, rel)