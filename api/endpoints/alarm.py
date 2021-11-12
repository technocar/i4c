from fastapi import Depends, Body, Path
from fastapi.security import HTTPBasicCredentials
import common
import models.alarm
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/alarm")


@router.get("/defs/{name}", response_model=models.alarm.AlarmDef, x_properties=dict(object="alarmdef", action="get"))
async def alarmdef_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/defs/{name}")),
    name: str = Path(...),
):
    return await models.alarm.alarmdef_get(credentials, name)
