from fastapi import Query
from fastapi.responses import PlainTextResponse
from I4cAPI import I4cApiRouter
from common import create_password

router = I4cApiRouter(include_path="/users")


@router.get("/create_password", response_class=PlainTextResponse, x_properties=dict(object="user", action="crepwd"))
async def snapshot(
        password: str = Query(...)):
    return create_password(password)
