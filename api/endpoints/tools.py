from datetime import datetime
from typing import List, Optional
from fastapi import Depends, Body, Path, Query
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
from starlette.responses import Response
import common
import models.log
import models.tools
import models.common
from I4cAPI import I4cApiRouter
from models import Device

router = I4cApiRouter(include_path="/tools")


@router.put("", status_code=201, response_class=Response, operation_id="tool_record", summary="Record tool change.")
async def tools_log_write(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("put/tools")),
        datapoint: models.tools.ToolDataPoint = Body(...)):
    """
    Record a tool change event. Updates if same device/timestamp/sequence/slot.
    """
    d = models.log.DataPointLog(timestamp=datapoint.timestamp,
                                sequence=datapoint.sequence,
                                device=datapoint.device,
                                data_id=datapoint.data_id,
                                value_text=datapoint.tool_id,
                                value_extra=datapoint.slot_number)
    await models.log.put_log_write(credentials, [d], override=True)


@router.delete("", status_code=204, response_class=Response, operation_id="tool_delete", summary="Delete tool change.")
async def tools_log_delete(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/tools")),
        datapointkey: models.tools.ToolDataPointKey = Body(...)):
    """
    Remove a tool change event.
    """
    d = models.log.DataPointKey(timestamp=datapointkey.timestamp,
                                sequence=datapointkey.sequence,
                                device=datapointkey.device,
                                data_id=datapointkey.data_id)
    await models.log.delete_log(credentials, d)


@router.get("", response_model=List[models.tools.ToolDataPointWithType], operation_id="tool_list",
            summary="List tool changes.")
async def tool_list(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/tools")),
        device: Device = Query(..., title="device"),
        timestamp: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
        sequence: Optional[int] = Query(None, description="sequence excluding this"),
        max_count: Optional[int] = Query(None)):
    """List tool change events."""
    return await models.tools.tool_list(credentials, device, timestamp, sequence, max_count)


@router.patch("/{tool_id}", response_model=models.common.PatchResponse, operation_id="tool_update",
              summary="Update tool.")
async def patch_tools(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/tools/{tool_id}")),
    tool_id: str = Path(...),
    patch: models.tools.ToolsPatchBody = Body(...),
):
    """
    Update or register a tool.
    """
    return await models.tools.patch_tool(credentials, tool_id, patch)


@router.get("/list_usage", response_model=List[models.tools.ToolItem], operation_id="tool_usage",
            summary="List tools.")
async def tool_list_usage(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/tools/list_usage")),
        tool_id: Optional[str] = Query(None, title="Tool id filter."),
        type: Optional[str] = Query(None, title="Type filter.")):
    """List tools and some statistics on their usage."""
    return await models.tools.tool_list_usage(credentials, tool_id=tool_id, type=type)
