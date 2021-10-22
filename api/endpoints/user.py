from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from common import create_password

router = APIRouter()


@router.get("/create_password", response_class=PlainTextResponse)
async def snapshot(
        password: str = Query(...)):
    return create_password(password)
