from fastapi import Depends, Body, HTTPException, Path
from fastapi.security import HTTPBasicCredentials
import common
import models.log
import models.tools
from I4cAPI import I4cApiRouter

router = I4cApiRouter()


def check_allow_tool_log_data_id(data_id):
    if data_id not in ('install_tool', 'remove_tool'):
        raise HTTPException(status_code=400, detail="Allowed data_ids are 'install_tool' and 'remove_tool'")


@router.put("", status_code=201, x_properties=dict(object="tool", action="log_write"))
async def tools_log_write(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("put/tools")),
        datapoint: models.log.DataPoint = Body(...)):
    check_allow_tool_log_data_id(datapoint.data_id)
    return await models.log.put_log_write(credentials, [datapoint], override=True)


@router.delete("", status_code=201, x_properties=dict(object="tool", action="log_delete"))
async def tools_log_delete(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/tools")),
        datapointkey: models.log.DataPointKey = Body(...)):
    check_allow_tool_log_data_id(datapointkey.data_id)
    return await models.log.delete_log(credentials, datapointkey)


@router.patch("/{tool_id}", response_model=models.common.PatchResponse, x_properties=dict(object="projects ver", action="patch"))
async def patch_tools(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/tools/{tool_id}")),
    tool_id: str = Path(...),
    patch: models.tools.ToolsPatchBody = Body(...),
):
    return await models.tools.patch_project_version(credentials, tool_id, patch)
