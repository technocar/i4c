from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, HTTPException, Body
from fastapi.security import HTTPBasicCredentials
import common
import models.stat
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/stat")


@router.get("/def", response_model=List[models.stat.StatDef], x_properties=dict(object="stat", action="list"))
async def stat_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/def")),
        id: Optional[str] = Query(None),
        user: Optional[str] = Query(None),
        name: Optional[str] = Query(None),
        name_mask: Optional[List[str]] = Query(None),
        type: Optional[str] = Query(None),):
    return await models.stat.stat_list(credentials, id, user, name, name_mask, type)


@router.get("/def/{id}", response_model=models.stat.StatDef, x_properties=dict(object="stat", action="get"))
async def stat_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/def/{id}")),
    id: str = Path(...),
):
    res = await models.stat.stat_list(credentials, id=id)
    if res is None:
        raise HTTPException(status_code=404, detail="No record found")
    return res


@router.post("/def", response_model=models.stat.StatDef, x_properties=dict(object="stat", action="post"))
async def stat_post(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/stat/def")),
    stat: models.stat.StatDefIn = Body(...),
):
    return await models.stat.stat_post(credentials, stat)


@router.delete("/def/{id}", status_code=200, x_properties=dict(object="stat", action="delete"))
async def stat_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/stat/def/{id}")),
    id: int = Path(...)
):
    return await models.stat.stat_delete(credentials, id)


@router.patch("def/{id}", response_model=models.common.PatchResponse, x_properties=dict(object="installations", action="patch"))
async def stat_patch(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/stat/def/{id}")),
    id: int = Path(...),
    patch: models.stat.StatPatchBody = Body(...),
):
    return await models.stat.stat_patch(credentials, id, patch)
