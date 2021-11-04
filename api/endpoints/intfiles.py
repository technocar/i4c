from typing import List, Optional
from fastapi import Depends, Path, Body, Query
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import StreamingResponse, FileResponse, Response

import common
import models.intfiles
from I4cAPI import I4cApiRouter

router = I4cApiRouter()


@router.get("", response_model=List[models.intfiles.FileDetail], x_properties=dict(object="intfiles", action="list"))
async def intfiles_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles")),
    name: Optional[str] = Query(None),
    min_ver: Optional[int] = Query(None),
    max_ver: Optional[int] = Query(None),
    hash: Optional[str] = Query(None),
):
    return await models.intfiles.intfiles_list(credentials, name, min_ver, max_ver, hash)


@router.get("/v/{ver}/{path:path}", response_class=StreamingResponse(Response, media_type="application/octet-stream"),
            x_properties=dict(object="intfiles", action="get"))
async def intfiles_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...)
):
    return await models.intfiles.intfiles_get(credentials, ver, path)


@router.put("/v/{ver}/{path:path}", status_code=201, x_properties=dict(object="intfiles", action="put"))
async def intfiles_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...),
    data: bytes = Body(..., media_type="application/octet-stream")
):
    return await models.intfiles.intfiles_put(credentials, ver, path, data)


@router.delete("/v/{ver}/{path:path}", status_code=201, x_properties=dict(object="intfiles", action="delete"))
async def intfiles_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...)
):
    return await models.intfiles.intfiles_delete(credentials, ver, path)
