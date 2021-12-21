from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Body
from fastapi.security import HTTPBasicCredentials
import models.log
import common
from I4cAPI import I4cApiRouter
from common.exceptions import I4cClientNotFound
from models import Device, DeviceAuto

router = I4cApiRouter(include_path="/log")


@router.get("/snapshot", response_model=models.log.Snapshot, operation_id="log_snapshot", allow_log=False)
async def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/snapshot")),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: DeviceAuto = Query("auto", title="Name of the devide", description="mill|lathe|gom|robot|auto")
):
    """Log snapshot at a given time"""
    return await models.log.get_snapshot(credentials, ts, device)


@router.get("/find", response_model=List[models.log.DataPoint], operation_id="log_list", allow_log=False)
async def find(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/find")),
        device: Device = Query(..., title="device"),
        timestamp: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        sequence: Optional[int] = Query(None, description="sequence excluding this"),
        before_count: Optional[int] = Query(None),
        after_count: Optional[int] = Query(None, description="when before_count and after_count both are None, then it defaults to after=1"),
        categ: Optional[models.log.MetaCategory] = Query(None),
        name: Optional[str] = Query(None),
        val: Optional[List[str]] = Query(None),
        extra: Optional[str] = Query(None),
        rel: Optional[str] = Query(None)
):
    """List log entries"""
    rs = await models.log.get_find(credentials, device, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel)
    if rs is None:
        raise I4cClientNotFound("No log record found")
    return rs


@router.get("/meta", response_model=List[models.log.Meta], operation_id="log_meta")
async def meta(credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/meta"))):
    """Retrieve log metadata"""
    return await models.log.get_meta(credentials)


@router.post("", status_code=201, operation_id="log_write", allow_log=False)
async def log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("post/log")),
        datapoints: List[models.log.DataPoint] = Body(...)):
    """Submit data to the log"""
    return await models.log.put_log_write(credentials, datapoints)


@router.get("/last_instance", response_model=models.log.LastInstance, operation_id="log_lastinstance")
async def last_instance(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/last_instance")),
        device: Device = Query(..., title="device")):
    """For Mazak machines, the last MTConnect instance"""
    return await models.log.get_last_instance(credentials, device)
