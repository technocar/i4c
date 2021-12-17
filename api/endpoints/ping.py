from typing import Optional, List, Dict, Any
from fastapi import Depends, Query, Path, Body, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from pydantic import BaseModel
import common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures

router = I4cApiRouter(include_path="/ping")


class Pong(BaseModel):
    data: Optional[str]


@router.get("/noop", response_model=Pong, x_properties=dict(object="ping", action="noop"))
async def noop_get(
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """This endpoint can be used to test API availability"""
    return {"data": data}


@router.post("/noop", response_model=Dict[Any, Any], x_properties=dict(object="ping", action="post"))
async def noop_post(
        data: Optional[Dict[Any, Any]] = Body(None, title="Will be given back as the response")):
    """This endpoint can be used to test POST method and json transport"""
    if data is None:
        data = {}
    return data


@router.get("/pwd", response_model=Pong, x_properties=dict(object="ping", action="pwd"))
async def pwd_get(
        credentials: HTTPBasicCredentials = Depends(HTTPBasic()),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """This endpoint tests password authentication. User "goodname" with password "goodpass" will be accepted."""
    if credentials.username != "goodname" or credentials.password != "goodpass":
        raise HTTPException(403)
    return {"data": data}


# TODO implement /signature


@router.get("/db", response_model=Pong, x_properties=dict(object="ping", action="db"))
async def db_get(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/ping/db")),
        data: Optional[str] = Query(None, title="Will be given back in the response")):
    """This endpoint can be used to test proper authentication and backend database access."""
    return {"data": data}
