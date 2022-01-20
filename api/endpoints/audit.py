from datetime import datetime
from typing import List, Optional
from fastapi import Depends, Query
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
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/audit")),
        before: Optional[datetime] = Query(None, title="Before timestamp, iso format."),
        after: Optional[datetime] = Query(None, title="After timestamp, iso format."),
        count: Optional[int] = Query(None, title="Record count."),
        object: Optional[str] = Query(None, title="Object."),
        action: Optional[str] = Query(None, title="Action."),

):
    """Get a list of audits."""
    before_s, after_s, count_s = before is not None, after is not None, count is not None
    c = sum(int(x) for x in (before_s, after_s, count_s))
    if c < 2:
        raise ValueError('Invalid (before, after, count) configuration.')

    return await models.audit.audit_list(credentials, before, after, count, object, action)
