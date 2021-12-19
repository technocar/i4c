from typing import Optional, List, Dict, Any
from fastapi import Depends, Query, Path, Body, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from pydantic import BaseModel
import common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures
from common.auth import check_signature

router = I4cApiRouter(include_path="/ping")


class Pong(BaseModel):
    data: Optional[str]


@router.get("/noop", response_model=Pong, operation_id="ping_noop",
            summary="Test API availability")
async def noop_get(
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test API availability."""
    return {"data": data}


@router.post("/noop", response_model=Dict[Any, Any], operation_id="ping_post",
            summary="Test API post")
async def noop_post(
        data: Optional[Dict[Any, Any]] = Body(None, title="Will be given back as the response")):
    """Test POST method and json transport."""
    if data is None:
        data = {}
    return data


@router.get("/pwd", response_model=Pong, operation_id="ping_pwd",
            summary="Test API password auth")
async def pwd_get(
        credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test password authentication. User "goodname" with password "goodpass" will be accepted."""
    if credentials.username != "goodname" or credentials.password != "goodpass":
        raise HTTPException(403)
    return {"data": data}


@router.get("/sign", response_model=Pong, operation_id="ping_sign",
            summary="Test API signature auth")
async def sign_get(
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
            summary="Test API w backend auth")
async def db_get(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/ping/db")),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """Test real authentication and backend database access."""
    return {"data": data}
