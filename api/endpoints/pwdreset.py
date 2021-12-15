from typing import List
from fastapi import Query, Depends, Body
from fastapi.security import HTTPBasicCredentials
import models.pwdreset
from I4cAPI import I4cApiRouter
import common

router = I4cApiRouter(include_path="/pwdreset")


@router.post("/init", status_code=201, tags=["user"], x_properties=dict(object="pwdreset", action="init"))
async def init(
        loginname: str
        ):
    "Reset user password"
    return await models.pwdreset.init(loginname)


@router.post("/setpass", response_model=models.users.LoginUserResponse, tags=["user"], x_properties=dict(object="pwdreset", action="set"))
async def setpass(param: models.pwdreset.SetPassParams = Body(...)):
    "Reset user password"
    return await models.pwdreset.setpass(param.loginname, param.token, param.password)


@router.get("", response_model=List[models.pwdreset.PwdresetOutboxItem], x_properties=dict(object="pwdreset", action="list"))
async def get_outbox_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/pwdreset"))
):
    return await models.pwdreset.get_outbox_list(credentials)


@router.post("/sent", status_code=201, tags=["user"], x_properties=dict(object="pwdreset", action="sent"))
async def sent(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("post/pwdreset/sent")),
        loginname: str = Query(...)
):
    return await models.pwdreset.sent(credentials, loginname)
