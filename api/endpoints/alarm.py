from fastapi import Depends, Body, Path, HTTPException
from fastapi.security import HTTPBasicCredentials
import common
import models.alarm
from I4cAPI import I4cApiRouter

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
    alarm_id, res = await models.alarm.alarmdef_get(credentials, name)
    if alarm_id is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res
