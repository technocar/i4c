from fastapi import Query
from fastapi.responses import PlainTextResponse
from I4cAPI import I4cApiRouter
import common

router = I4cApiRouter(include_path="/users")


@router.get("/create_password", response_class=PlainTextResponse, include_in_schema=False)
async def create_password(password: str = Query(...)):
    return common.create_password(password)
