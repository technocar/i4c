from fastapi import Depends, Path, File, UploadFile, Body
from fastapi.security import HTTPBasicCredentials

import common
import models.intfiles
from I4cAPI import I4cApiRouter

router = I4cApiRouter()


@router.put("/v/{ver}/{path:path}", x_properties=dict(object="intfiles", action="put"))
async def intfiles_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/intfiles/v/{ver}/{path:path}")),
    ver: int = Path(...),
    path: str = Path(...),
    data=Body(..., media_type="application/octet-stream")
):
    return await models.intfiles.intfiles_put(credentials, ver, path, data)

