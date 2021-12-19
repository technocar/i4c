from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
import common
import models.stat
import models.common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures
from common.exceptions import I4cClientNotFound

router = I4cApiRouter(include_path="/stat")


@router.get("/def", response_model=List[models.stat.StatDef], operation_id="stat_def_list")
async def stat_list(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/stat/def")),
        id: Optional[int] = Query(None),
        user_id: Optional[str] = Query(None),
        name: Optional[str] = Query(None),
        name_mask: Optional[List[str]] = Query(None),
        type: Optional[models.stat.StatTimeseriesType] = Query(None),):
    """List saved queries."""
    return await models.stat.stat_list(credentials, id, user_id, name, name_mask, type)


@router.get("/def/{id}", response_model=models.stat.StatDef, operation_id="stat_def_get")
async def stat_get(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("get/stat/def/{id}")),
    id: int = Path(...),
):
    """Get a saved query."""
    res = await models.stat.stat_list(credentials, id=id)
    if len(res) == 0:
        raise I4cClientNotFound("No record found")
    return res[0]


@router.post("/def", response_model=models.stat.StatDef, operation_id="stat_def_save")
async def stat_post(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("post/stat/def")),
    stat: models.stat.StatDefIn = Body(...),
):
    """Save a query."""
    return await models.stat.stat_post(credentials, stat)


@router.delete("/def/{id}", status_code=200, operation_id="stat_def_delete", features=['delete any'])
async def stat_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/stat/def/{id}", ask_features=['delete any'])),
    id: int = Path(...)
):
    """Delete a saved query."""
    return await models.stat.stat_delete(credentials, id)


@router.patch("/def/{id}", response_model=models.common.PatchResponse, operation_id="stat_def_update", features=['patch any'])
async def stat_patch(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/stat/def/{id}", ask_features=['patch any'])),
    id: int = Path(...),
    patch: models.stat.StatPatchBody = Body(...),
):
    """Update a saved query."""
    return await models.stat.stat_patch(credentials, id, patch)


@router.get("/data/{id}", response_model=models.stat.StatData, operation_id="stat_data")
async def stat_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/data/{id}")),
    id: int = Path(...),
):
    """Run query."""
    return await models.stat.statdata_get(credentials, id)


@router.get("/xymeta", response_model=models.stat.StatXYMeta, operation_id="stat_xymeta")
async def get_xymeta(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/xymeta")),
    after: Optional[datetime] = Query(None, title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z, default 1 year"),
):
    """Get metadata for xy queries."""
    return await models.stat.get_xymeta(credentials, after)
