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


@router.get("/snapshot", response_model=models.log.Snapshot, x_properties=dict(object="datapoint", action="snapshot"), allow_log=False)
async def snapshot(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/snapshot")),
    ts: datetime = Query(..., title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    device: DeviceAuto = Query(..., title="Name of the devide", description="mill|lathe|gom|robot|auto")
):
    return await models.log.get_snapshot(credentials, ts, device)


@router.get("/find", response_model=List[models.log.DataPoint], x_properties=dict(object="datapoint", action="list"))
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
    rs = await models.log.get_find(credentials, device, timestamp, sequence, before_count, after_count, categ, name, val, extra, rel)
    if rs is None:
        raise I4cClientNotFound("No log record found")
    return rs


@router.get("/meta", response_model=List[models.log.Meta], x_properties=dict(object="meta", action="list"))
async def meta(credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/meta"))):
    return await models.log.get_meta(credentials)


@router.post("", status_code=201, x_properties=dict(object="datapoint", action="post"), allow_log=False)
async def log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("post/log")),
        datapoints: List[models.log.DataPoint] = Body(...)):
    return await models.log.put_log_write(credentials, datapoints)


@router.get("/last_instance", response_model=models.log.LastInstance, x_properties=dict(object="datapoint", action="lastinstance"))
async def last_instance(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/last_instance")),
        device: Device = Query(..., title="device")):
    return await models.log.get_last_instance(credentials, device)
