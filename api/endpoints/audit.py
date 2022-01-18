from typing import List
from fastapi import Depends
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request
import common
import models.audit
from I4cAPI import I4cApiRouter

router = I4cApiRouter(include_path="/audit")


# todo 1: ****************
@router.get("", response_model=List[models.audit.AuditListItem], operation_id="audit_list", summary="List audites.")
async def audit_list(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/audit"))
):
    """Get a list of audits."""
    return await models.audit.audit_list(credentials)
