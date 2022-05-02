from typing import Optional
from fastapi import Depends, Path, Body
from starlette.requests import Request
from starlette.responses import Response
import common
import models.settings
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures

router = I4cApiRouter(include_path="/settings")


@router.get("/{key}", response_model=Optional[str], operation_id="settings_get", summary="Retrieve setting.",
            features=['access private', 'noaudit'])
async def settings_get(
        request: Request,
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/settings/{key}", ask_features=['access private', 'noaudit'])),
        key: str = Path(...)):
    """Get a setting."""
    return await models.settings.settings_get(credentials, key)


@router.put("/{key}", status_code=201, response_class=Response, operation_id="settings_set", summary="Write setting.",
            features=['access private'])
async def settings_put(
        request: Request,
        credentials: CredentialsAndFeatures = Depends(common.security_checker("put/settings/{key}", ask_features=['access private'])),
        key: str = Path(...),
        value: models.settings.ValueIn = Body(...)):
    """Update a setting."""
    await models.settings.settings_put(credentials, key, value)
