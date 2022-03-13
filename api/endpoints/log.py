from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Body
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
from starlette.responses import Response
import models.log
import common
from I4cAPI import I4cApiRouter
from common.exceptions import I4cClientNotFound
from models import Device, DeviceAuto

router = I4cApiRouter(include_path="/log")


@router.get("/snapshot", response_model=models.log.Snapshot, operation_id="log_snapshot", summary="Snapshot.",
            allow_log=False)
async def snapshot(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/snapshot")),
    ts: datetime = Query(..., title="Timestamp, iso format."),
    device: DeviceAuto = Query("auto", title="Name of the device, or `auto` for the active at the time.")
):
    """Log snapshot at a given time."""
    return await models.log.get_snapshot(credentials, ts, device)


@router.get("/find", response_model=List[models.log.DataPoint], operation_id="log_list", allow_log=False,
            summary="Search the log.")
async def find(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/find")),
        device: Device = Query(..., title="Device."),
        timestamp: Optional[datetime] = Query(None, title="Around timestamp, iso format."),
        sequence: Optional[int] = Query(None, title="Sequence, after or before."),
        before_count: Optional[int] = Query(None, title="Number of log records before the timestamp."),
        after_count: Optional[int] = Query(None, description="Number of log records after the timestamp. Defaults to 1 if before is omitted, 0 otherwise."),
        categ: Optional[models.log.MetaCategory] = Query(None, title="Log data category."),
        data_id: Optional[str] = Query(None, title="Log data type."),
        val: Optional[List[str]] = Query(None, title="Value of the log item."),
        extra: Optional[str] = Query(None, title="Extra of the log item."),
        rel: Optional[str] = Query(None, title="Relation for the val or extra.")
):
    """List log entries."""
    rs = await models.log.get_find(credentials, device, timestamp, sequence, before_count, after_count, categ, data_id, val, extra, rel)
    if rs is None:
        raise I4cClientNotFound("No log record found")
    return rs

@router.get("/meta", response_model=List[models.log.Meta], operation_id="log_meta", summary="Get log metadata.")
async def meta(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/meta"))):
    """Retrieve log metadata."""
    return await models.log.get_meta(credentials)


@router.post("", status_code=201, response_class=Response, operation_id="log_write", allow_log=False, summary="Write log.")
async def log_write(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("post/log")),
        datapoints: List[models.log.DataPoint] = Body(...)):
    """Submit data to the log."""
    await models.log.put_log_write(credentials, datapoints)


@router.get("/last_instance", response_model=models.log.LastInstance, operation_id="log_lastinstance",
            summary="Last known instance of a device.")
async def last_instance(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/last_instance")),
        device: Device = Query(..., title="Device.")):
    """For Mazak machines, the last seen MTConnect instance. Can be used to determine if we need to query back data."""
    return await models.log.get_last_instance(credentials, device)
