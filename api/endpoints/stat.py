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


@router.get("/def", response_model=List[models.stat.StatDef], operation_id="stat_list",
            summary="List saved queries.")
async def stat_list(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/stat/def")),
        id: Optional[int] = Query(None),
        user_id: Optional[str] = Query(None),
        name: Optional[str] = Query(None),
        name_mask: Optional[List[str]] = Query(None),
        type: Optional[models.stat.StatTimeseriesType] = Query(None),):
    """List saved queries."""
    return await models.stat.stat_list(credentials, id, user_id, name, name_mask, type)


@router.get("/def/{id}", response_model=models.stat.StatDef, operation_id="stat_get",
            summary="Retrieve saved query.")
async def stat_get(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("get/stat/def/{id}")),
    id: int = Path(...),
):
    """Get a saved query."""
    res = await models.stat.stat_list(credentials, id=id)
    if len(res) == 0:
        raise I4cClientNotFound("No record found")
    return res[0]


@router.post("/def", response_model=models.stat.StatDef, operation_id="stat_save", summary="Save query.")
async def stat_post(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("post/stat/def")),
    stat: models.stat.StatDefIn = Body(...),
):
    """Save a query."""
    return await models.stat.stat_post(credentials, stat)


@router.delete("/def/{id}", status_code=200, operation_id="stat_delete", features=['delete any'],
               summary="Delete query.")
async def stat_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/stat/def/{id}", ask_features=['delete any'])),
    id: int = Path(...)
):
    """Delete a saved query."""
    return await models.stat.stat_delete(credentials, id)


@router.patch("/def/{id}", response_model=models.common.PatchResponse, operation_id="stat_update",
              summary="Update query.", features=['patch any'])
async def stat_patch(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/stat/def/{id}", ask_features=['patch any'])),
    id: int = Path(...),
    patch: models.stat.StatPatchBody = Body(...),
):
    """Update a saved query."""
    return await models.stat.stat_patch(credentials, id, patch)


@router.get("/data/{id}", response_model=models.stat.StatData, operation_id="stat_run", summary="Run query.")
async def stat_data_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/data/{id}")),
    id: int = Path(...),
):
    """Run query."""
    return await models.stat.statdata_get(credentials, id)


@router.get("/objmeta", response_model=List[models.stat.StaMetaObject], operation_id="stat_objmeta",
            summary="Metadata for chart objects.")
async def get_objmeta(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/objmeta")),
    after: Optional[datetime] = Query(None, title="timestamp", description="Iso format, defaults to last year."),
):
    """Get metadata for xy queries."""
    return await models.stat.get_objmeta(credentials, after)
