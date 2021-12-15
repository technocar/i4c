from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
import common
import models.settings
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/settings")


@router.get("/{key}", response_model=str, x_properties=dict(object="settings", action="get"))
async def settings_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/settings/{key}")),
        key: str = Path(...)):
    return await models.settings.settings_get(credentials, key)


@router.put("/{key}", status_code=201, x_properties=dict(object="settings", action="set"))
async def settings_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/settings/{key}")),
    key: str = Path(...),
    value: models.settings.ValueIn = Body(...),
):
    """Create or update settings definition."""
    return await models.settings.settings_put(credentials, key, value)
