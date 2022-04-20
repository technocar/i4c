import asyncio
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Depends, Query, Body, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from starlette.requests import Request
import common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures, DatabaseConnection
from common.auth import check_signature

router = I4cApiRouter(include_path="/ping")


class Pong(BaseModel):
    data: Optional[str]


@router.get("/noop", response_model=Pong, allow_log=False, operation_id="ping_noop",
            summary="Test API availability.")
async def noop_get(
        request: Request,
        data: Optional[str] = Query(None, title="Will be given back in the response"),
        wait: Optional[float] = Query(None, title="Only return after this many seconds")):
    """Test API availability."""
    if wait is not None:
        await asyncio.sleep(wait)
    return {"data": data}


@router.get("/datetime", response_model=datetime, operation_id="ping_datetime",)
async def get_datetime(
    request: Request,
    dt: Optional[datetime] = Query(None, title="Timestamp, iso format, will be given back.")
):
    """
    Test datetime formatting, and/or query the server time. The dt parameter will be given back verbatim.
    If omitted, the current time with timezone will be given back.
    """
    return dt or datetime.now().astimezone()


@router.post("/noop", response_model=Dict[Any, Any], allow_log=False, operation_id="ping_post",
            summary="Test API POST.")
async def noop_post(
        request: Request,
        data: Optional[Dict[Any, Any]] = Body(None, title="Will be given back as the response")):
    """Test POST method and json transport."""
    if data is None:
        data = {}
    return data


@router.get("/bin", response_class=StreamingResponse(..., media_type="application/octet-stream"),
    operation_id="ping_download", summary="Test binary download")
async def get_bin(
        request: Request,
        size: Optional[int] = Query(4096, title="File size in bytes, defaults to 4096."),
        char: Optional[str] = Query("00", title="The byte to repeat, hex. Default 00."),
        delay: Optional[int] = Query(0, title="Delay between 64K chunks, millisecond. Default 0.")):

    char = bytes([int(char, 16)])

    async def create():
        to_send = size
        while to_send > 65536:
            yield char * 65536
            to_send -= 65536
            if delay > 0:
                await asyncio.sleep(delay / 1000.0)
        else:
            yield char * to_send

    return StreamingResponse(content=create(), media_type="application/octet-stream")


class PingBinReport(BaseModel):
    chunks: int
    digest: str
    size: int
    upload_start: datetime
    upload_finish: datetime

__oa = {"requestBody": {"content": {"application/octet-stream": {"schema": {"title": "Data", "type": "string", "format": "binary"}}}}}

@router.post("/bin", response_model=PingBinReport, allow_log=False, operation_id="ping_upload",
            summary="Test binary upload.", disconnect_guard=False, openapi_extra=__oa)
async def post_bin(
        request: Request):
    """Test POST method and binary transport. Will report the length and the sha384 hash of the data, and stats."""

    st = datetime.now().astimezone()

    h = hashlib.sha384()
    l = 0
    c = 0
    async for chunk in request.stream():
        h.update(chunk)
        l += len(chunk)
        c += 1
    h = h.digest().hex()

    en = datetime.now().astimezone()

    report = dict(chunks=c, digest=h, size=l, upload_start=st, upload_finish=en)

    return report


@router.get("/pwd", response_model=Pong, allow_log=False, operation_id="ping_pwd",
            summary="Test API password auth.")
async def pwd_get(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test password authentication. User "goodname" with password "goodpass" will be accepted."""
    if credentials.username != "goodname" or credentials.password != "goodpass":
        raise HTTPException(403)
    return {"data": data}


@router.get("/sign", response_model=Pong, allow_log=False, operation_id="ping_sign",
            summary="Test API signature auth.")
async def sign_get(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """
    Test signature authentication. User "goodname" with private key "Jzjk5ifxGQm8JkTiM8mv54hj2U8C6LGp547KdOMLv64=" will
    be accepted.
    """

    if credentials.username != "goodname":
        raise HTTPException(403)

    ok, msg = check_signature(credentials.password, "1mTHEDm5OnMpCx9wfU/pRZiFWwBrW9sN4bY3nYL3/u8=")
    if not ok:
        raise HTTPException(403, detail={"error": msg})

    return {"data": data}


@router.get("/db", response_model=Pong, operation_id="ping_db",
            summary="Test API db backend auth.")
async def db_get(
        request: Request,
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/ping/db")),
        data: Optional[str] = Query(None, title="Will be given back in the response"),
        wait: Optional[float] = Query(0, title="Only return after this many seconds")):
    """Test real authentication and backend database access."""
    async with DatabaseConnection() as conn:
        reply = await conn.fetchval("select $1::varchar from pg_sleep($2::double precision)", data, wait)

    return {"data": reply}
