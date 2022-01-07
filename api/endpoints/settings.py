from fastapi import Depends, Path, Body
from fastapi.security import HTTPBasicCredentials
import common
import models.settings
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures

router = I4cApiRouter(include_path="/settings")


@router.get("/{key}", response_model=str, operation_id="settings_get", summary="Retrieve setting.",
            features=['access private'])
async def settings_get(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/settings/{key}", ask_features=['access private'])),
        key: str = Path(...)):
    """Get a setting."""
    return await models.settings.settings_get(credentials, key)


@router.put("/{key}", status_code=201, operation_id="settings_set", summary="Write setting.")
async def settings_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/settings/{key}")),
    key: str = Path(...),
    value: models.settings.ValueIn = Body(...),
):
    """Create or update a setting."""
    return await models.settings.settings_put(credentials, key, value)
