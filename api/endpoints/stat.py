from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.stat
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/stat")


@router.get("/def", response_model=List[models.stat.StatDef], x_properties=dict(object="stat", action="list"))
async def stat_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/stat/def")),
        user: Optional[str] = Query(None),
        name: Optional[str] = Query(None),
        name_mask: Optional[List[str]] = Query(None),
        type: Optional[str] = Query(None),):
    return await models.stat.stat_list(credentials, user, name, name_mask, type)
