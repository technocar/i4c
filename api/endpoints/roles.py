from typing import List

from fastapi import Query, Depends
from fastapi.security import HTTPBasicCredentials

import models.roles
from I4cAPI import I4cApiRouter
import common

router = I4cApiRouter(include_path="/roles")
path_list = []


@router.get("", response_model=List[models.roles.Role], x_properties=dict(object="roles", action="list"))
async def get_roles(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/roles")),
):
    return await models.roles.get_roles(credentials, path_list)
