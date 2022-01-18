from typing import List
from fastapi import Depends, Body
from fastapi.security import HTTPBasicCredentials
from starlette.responses import Response

import models.pwdreset
from I4cAPI import I4cApiRouter
import common
import models.users

router = I4cApiRouter(include_path="/pwdreset")


@router.post("/init", status_code=201, response_class=Response, tags=["user"], operation_id="pwdreset_init", summary="Initiate password reset.")
async def init(
        loginname: models.pwdreset.LoginName = Body(...)
        ):
    "Initiates password reset. Creates token for sending by email."
    await models.pwdreset.init(loginname.loginname)


@router.post("/setpass", response_model=models.users.UserWithPrivs, tags=["user"], operation_id="pwdreset_set_pass",
             summary="Reset password.")
async def setpass(param: models.pwdreset.SetPassParams = Body(...)):
    "Reset user password using a password reset token."
    return await models.pwdreset.setpass(param.loginname, param.token, param.password)


@router.get("", response_model=List[models.pwdreset.PwdresetOutboxItem], operation_id="pwdreset_list",
            summary="List password reset tokens.")
async def get_outbox_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/pwdreset"))
):
    """List unsent password reset tokens."""
    return await models.pwdreset.get_outbox_list(credentials)


# TODO this thing still advertises json response
@router.post("/sent", status_code=201, tags=["user"], operation_id="pwdreset_mark_sent", summary="Mark token as sent.")
async def sent(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("post/pwdreset/sent")),
        loginname: models.pwdreset.LoginName = Body(...)
):
    """Mark password reset token sent."""
    return await models.pwdreset.sent(credentials, loginname.loginname)
