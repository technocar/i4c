from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Body, Path, HTTPException, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.alarm
from I4cAPI import I4cApiRouter
from models import CommonStatusEnum
import pytz

router = I4cApiRouter(include_path="/alarm")


@router.put("/defs/{name}", response_model=models.alarm.AlarmDef, x_properties=dict(object="alarmdef", action="put"))
async def alarmdef_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/alarm/defs/{name}")),
    name: str = Path(...),
    alarm: models.alarm.AlarmDefIn = Body(...),
):
    return await models.alarm.alarmdef_put(credentials, name, alarm)


@router.get("/defs/{name}", response_model=models.alarm.AlarmDef, x_properties=dict(object="alarmdef", action="get"))
async def alarmdef_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/defs/{name}")),
    name: str = Path(...),
):
    res = await models.alarm.alarmdef_get(credentials, name)
    if res is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res


@router.get("/defs", response_model=List[models.alarm.AlarmDef], x_properties=dict(object="alarmdef", action="list"))
async def alarmdef_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/defs")),
    name_mask: Optional[str] = Query(None),
    report_after: Optional[datetime] = Query(None, title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    subs_status: Optional[CommonStatusEnum] = Query(None),
    subs_method: Optional[models.alarm.AlarmMethod] = Query(None),
    subs_address: Optional[str] = Query(None),
    subs_address_mask: Optional[str] = Query(None),
    subs_user: Optional[str] = Query(None),
    subs_user_mask: Optional[str] = Query(None)
):
    return await models.alarm.alarmdef_list(credentials, name_mask, report_after,
                                            subs_status, subs_method, subs_address, subs_address_mask, subs_user, subs_user_mask)


@router.get("/subs", response_model=List[models.alarm.AlarmSub], x_properties=dict(object="alarmsub", action="list"))
async def alarmsub_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subs")),
        id: Optional[str] = Query(None),
        group: Optional[str] = Query(None),
        group_mask: Optional[str] = Query(None),
        user: Optional[str] = Query(None),
        user_name: Optional[str] = Query(None),
        user_name_mask: Optional[str] = Query(None),
        method: Optional[models.alarm.AlarmMethod] = Query(None),
        status: Optional[CommonStatusEnum] = Query(None),
        address: Optional[str] = Query(None),
        address_mask: Optional[str] = Query(None),
        alarm: Optional[str] = Query(None)):
    return await models.alarm.alarmsub_list(credentials, id, group, group_mask, user, user_name, user_name_mask,
                                            method, status, address, address_mask, alarm)


@router.get("/subsgroups", response_model=List[str], x_properties=dict(object="subsgroups", action="list"))
async def alarmsub_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subsgroups"))):
    return await models.alarm.subsgroups_list(credentials)


@router.get("/subs/{id}", response_model=models.alarm.AlarmSub, x_properties=dict(object="alarmsub", action="get"))
async def alarmsub_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subs/{id}")),
        id: int = Path(...)):
    res = await models.alarm.alarmsub_list(credentials, id=id)
    if len(res) > 0:
        return res[0]
    raise HTTPException(status_code=404, detail="No record found")


@router.post("/subs", response_model=models.alarm.AlarmSub, x_properties=dict(object="alarmsub", action="post"))
async def post_alarmsub(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/alarm/subs")),
    alarmsub: models.alarm.AlarmSubIn = Body(...),
):
    return await models.alarm.post_alarmsub(credentials, alarmsub)


@router.patch("/subs/{id}", response_model=models.common.PatchResponse, x_properties=dict(object="alarmsub", action="patch"))
async def patch_alarmsub(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/alarm/subs/{id}")),
    id: int = Path(...),
    patch: models.alarm.AlarmSubPatchBody = Body(...),
):
    return await models.alarm.patch_alarmsub(credentials, id, patch)


@router.post("/events/check", response_model=List[models.alarm.AlarmEventCheckResult], x_properties=dict(object="alarmevent", action="check"))
async def check_alarmevent(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/alarm/events/check")),
    alarm: Optional[str] = Query(None),
    max_count: Optional[int] = Query(None)
):
    def hun_tz(dt):
        tz = pytz.timezone("Europe/Budapest")
        return tz.localize(dt)

    # return await models.alarm.check_alarmevent(credentials, alarm, max_count, override_last_check=hun_tz(datetime(2021,10,27,13,21)), override_now=hun_tz(datetime(2021,10,27,13,30)))
    return await models.alarm.check_alarmevent(credentials, alarm, max_count)

