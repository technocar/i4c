from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body
from fastapi.security import HTTPBasicCredentials
import models.log
import common
from models import Device, DeviceAuto

router = APIRouter()


@router.get("/snapshot", response_model=models.log.Snapshot)
async def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker()),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: DeviceAuto = Query(..., title="Name of the devide", description="mill|lathe|gom|robot|auto")
):
    return await models.log.get_snapshot(credentials, ts, device)


@router.get("/find", response_model=List[models.log.DataPoint])
async def find(
        credentials: HTTPBasicCredentials = Depends(common.security_checker()),
        device: Device = Query(..., title="device"),
        timestamp: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        sequence: Optional[int] = Query(None, description="sequence excluding this"),
        before_count: Optional[int] = Query(None),
        after_count: Optional[int] = Query(None, description="when before_count and after_count both are None, then it defaults to after=1"),
        categ: Optional[str] = Query(None, description="“condition”, “event” or “sample”"),
        name: Optional[str] = Query(None),
        val: Optional[List[str]] = Query(None),
        extra: Optional[str] = Query(None),
        rel: Optional[str] = Query(None)):
    return await models.log.get_find(credentials, device, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel)


@router.get("/meta", response_model=List[models.log.Meta])
async def meta(credentials: HTTPBasicCredentials = Depends(common.security_checker())):
    return await models.log.get_meta(credentials)


@router.post("/", status_code=201)
async def log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker()),
        datapoints: List[models.log.DataPoint] = Body(...)):
    return await models.log.put_log_write(credentials, datapoints)


@router.get("/last_instance", response_model=models.log.LastInstance)
async def last_instance(
        credentials: HTTPBasicCredentials = Depends(common.security_checker()),
        device: Device = Query(..., title="device")):
    return await models.log.get_last_instance(credentials, device)
