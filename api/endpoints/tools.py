from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Body, Path, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.log
import models.tools
from I4cAPI import I4cApiRouter
from models import Device

router = I4cApiRouter(include_path="/tools")


@router.put("", status_code=201, x_properties=dict(object="tool", action="put"))
async def tools_log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("put/tools")),
        datapoint: models.tools.ToolDataPoint = Body(...)):
    d = models.log.DataPoint(timestamp=datapoint.timestamp,
                             sequence=datapoint.sequence,
                             device=datapoint.device,
                             data_id=datapoint.data_id,
                             value_text=datapoint.tool_id,
                             value_extra=datapoint.slot_number)
    return await models.log.put_log_write(credentials, [d], override=True)


@router.delete("", status_code=200, x_properties=dict(object="tool", action="delete"))
async def tools_log_delete(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/tools")),
        datapointkey: models.tools.ToolDataPointKey = Body(...)):
    d = models.log.DataPointKey(timestamp=datapointkey.timestamp,
                                sequence=datapointkey.sequence,
                                device=datapointkey.device,
                                data_id=datapointkey.data_id)
    return await models.log.delete_log(credentials, d)


@router.patch("/{tool_id}", response_model=models.common.PatchResponse, x_properties=dict(object="tools", action="patch"))
async def patch_tools(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/tools/{tool_id}")),
    tool_id: str = Path(...),
    patch: models.tools.ToolsPatchBody = Body(...),
):
    return await models.tools.patch_project_version(credentials, tool_id, patch)


@router.get("/list", response_model=List[models.tools.ToolDataPointType], x_properties=dict(object="tools", action="list"))
async def tool_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/log/find")),
        device: Device = Query(..., title="device"),
        timestamp: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        max_count: Optional[int] = Query(None)):
    return await models.tools.tool_list(credentials, device, timestamp, max_count)


@router.get("/list_usage", response_model=List[models.tools.ToolItem], x_properties=dict(object="tools", action="list_usage"))
async def tool_list_usage(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/tools/list_usage"))):
    return await models.tools.tool_list_usage(credentials)
