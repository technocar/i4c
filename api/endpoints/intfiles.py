import os
from typing import List, Optional
from fastapi import Depends, Path, Body, Query
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import FileResponse
import common
import models.intfiles
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/intfiles")


@router.get("", response_model=List[models.intfiles.FileDetail], operation_id="intfile_list")
async def intfiles_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles")),
    name: Optional[str] = Query(None),
    name_mask: Optional[List[str]] = Query(None),
    min_ver: Optional[int] = Query(None),
    max_ver: Optional[int] = Query(None),
    hash: Optional[str] = Query(None),
):
    """List internal files."""
    return await models.intfiles.intfiles_list(credentials, name, name_mask, min_ver, max_ver, hash)


@router.get("/v/{ver}/{path:path}", response_class=FileResponse(..., media_type="application/octet-stream"),
            operation_id="intfile_download")
async def intfiles_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...)
):
    """Download an internal file."""
    return await models.intfiles.intfiles_get(credentials, ver, path)


@router.put("/v/{ver}/{path:path}", status_code=201, operation_id="intfile_upload")
async def intfiles_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...),
    data: bytes = Body(..., media_type="application/octet-stream")
):
    """Upload an internal file."""
    return await models.intfiles.intfiles_put(credentials, ver, path, data)


@router.delete("/v/{ver}/{path:path}", status_code=200, operation_id="intfile_delete")
async def intfiles_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...)
):
    """Delete an internal file."""
    return await models.intfiles.intfiles_delete(credentials, ver, path)
