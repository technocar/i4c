from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.batch
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/batch")


@router.get("", response_model=List[models.batch.ListItem], x_properties=dict(object="batch", action="list"))
async def batch_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/batch")),
        project: Optional[str] = Query(None),
        after: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z")):
    return await models.batch.batch_list(credentials, project, after)
