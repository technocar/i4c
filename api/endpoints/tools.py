from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Body, Path, Query
from fastapi.security import HTTPBasicCredentials
import common
import models.log
import models.tools
import models.common
from I4cAPI import I4cApiRouter
from models import Device

router = I4cApiRouter(include_path="/tools")


@router.put("", status_code=201, operation_id="tool_record", summary="Record tool change.")
async def tools_log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("put/tools")),
        datapoint: models.tools.ToolDataPoint = Body(...)):
    """
    Record a tool change event. Updates if same device/timestamp/sequence/slot.
    """
    # TODO data_id should be fixed
    d = models.log.DataPoint(timestamp=datapoint.timestamp,
                             sequence=datapoint.sequence,
                             device=datapoint.device,
                             data_id=datapoint.data_id,
                             value_text=datapoint.tool_id,
                             value_extra=datapoint.slot_number)
    return await models.log.put_log_write(credentials, [d], override=True)


# TODO response_model?
@router.delete("", status_code=200, operation_id="tool_delete", summary="Delete tool change.")
async def tools_log_delete(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/tools")),
        datapointkey: models.tools.ToolDataPointKey = Body(...)):
    """
    Remove a tool change event.
    """
    # TODO data_id should be fixed
    d = models.log.DataPointKey(timestamp=datapointkey.timestamp,
                                sequence=datapointkey.sequence,
                                device=datapointkey.device,
                                data_id=datapointkey.data_id)
    return await models.log.delete_log(credentials, d)


@router.patch("/{tool_id}", response_model=models.common.PatchResponse, operation_id="tool_update",
              summary="Update or create tool.")
async def patch_tools(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/tools/{tool_id}")),
    tool_id: str = Path(...),
    patch: models.tools.ToolsPatchBody = Body(...),
):
    """
    Update or register a tool.
    """
    # without
    return await models.tools.patch_project_version(credentials, tool_id, patch)   # TODO !!! wut? project version?


@router.get("", response_model=List[models.tools.ToolDataPointType], operation_id="tool_list",
            summary="List tool changes.")
async def tool_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/tools")),
        device: Device = Query(..., title="device"),
        timestamp: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        sequence: Optional[int] = Query(None, description="sequence excluding this"),
        max_count: Optional[int] = Query(None)):
    """List tool change events."""
    return await models.tools.tool_list(credentials, device, timestamp, sequence, max_count)


@router.get("/list_usage", response_model=List[models.tools.ToolItem], operation_id="tool_usage",
            summary="List tools.")
async def tool_list_usage(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/tools/list_usage"))):
    """List tools and some statistics on their usage."""
    return await models.tools.tool_list_usage(credentials)
