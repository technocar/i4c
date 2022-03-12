from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Depends, Query, Body, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from pydantic import BaseModel
from starlette.requests import Request
import common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures
from common.auth import check_signature

router = I4cApiRouter(include_path="/ping")


class Pong(BaseModel):
    data: Optional[str]


@router.get("/noop", response_model=Pong, allow_log=False, operation_id="ping_noop",
            summary="Test API availability.")
async def noop_get(
        request: Request,
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test API availability."""
    return {"data": data}


@router.get("/datetime", operation_id="ping_datetime",)
async def get_datetime(
    dt: Optional[datetime] = Query(None, title="Around timestamp, iso format.")
):
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
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test real authentication and backend database access."""
    return {"data": data}
