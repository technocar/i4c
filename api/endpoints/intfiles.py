# -*- coding: utf-8 -*-
from typing import List, Optional
from fastapi import Depends, Path, Body, Query
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import FileResponse, Response
from starlette.requests import Request
import common
import models.intfiles
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/intfiles")


@router.get("", response_model=List[models.intfiles.FileDetail], operation_id="intfile_list",
            summary="List internal files")
async def intfiles_list(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles")),
    name: Optional[str] = Query(None, title="Exact name."),
    name_mask: Optional[List[str]] = Query(None, title="Search mask for the name."),
    min_ver: Optional[int] = Query(None, title="Minimum version."),
    max_ver: Optional[int] = Query(None, title="Maximum version."),
    hash: Optional[str] = Query(None, title="Sha384 hash of the content."),
):
    """List internal files."""
    return await models.intfiles.intfiles_list(credentials, name, name_mask, min_ver, max_ver, hash)


@router.get("/v/{ver}/{path:path}", response_class=FileResponse(..., media_type="application/octet-stream"),
            operation_id="intfile_download", summary="Download internal file.")
async def intfiles_get(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...)
):
    """Download an internal file."""
    return await models.intfiles.intfiles_get(credentials, ver, path)


@router.put("/v/{ver}/{path:path}", status_code=201, response_class=Response, operation_id="intfile_upload", summary="Upload internal file.")
async def intfiles_put(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(..., title="Version."),
    path: str = Path(..., title="Unique name, optionally including path."),
    data: bytes = Body(..., media_type="application/octet-stream")
):
    """Upload an internal file."""
    await models.intfiles.intfiles_put(credentials, ver, path, data)


@router.delete("/v/{ver}/{path:path}", status_code=204, response_class=Response, operation_id="intfile_delete", summary="Delete internal file.")
async def intfiles_delete(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(..., title="Version."),
    path: str = Path(..., title="Unique name.")
):
    """Delete an internal file."""
    await models.intfiles.intfiles_delete(credentials, ver, path)
