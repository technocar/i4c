from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, Body
from fastapi.security import HTTPBasicCredentials
import models.workpiece
import models.common
import common
from I4cAPI import I4cApiRouter
from models import ProjectStatusEnum, WorkpieceStatusEnum

router = I4cApiRouter()


@router.get("/{id}", response_model=models.workpiece.Workpiece, x_properties=dict(object="workpiece", action="get"))
async def get_workpiece(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/workpiece/{id}")),
    id: str = Path(...)
):
    return await models.workpiece.get_workpiece(credentials, id)


@router.get("", response_model=List[models.workpiece.Workpiece], x_properties=dict(object="workpiece", action="list"))
async def list_workpiece(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/workpiece")),
    before: Optional[datetime] = Query(None),
    after: Optional[datetime] = Query(None),
    id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    status: Optional[WorkpieceStatusEnum] = Query(None),
    note_user: Optional[str] = Query(None),
    note_text: Optional[str] = Query(None),
    note_before: Optional[datetime] = Query(None),
    note_after: Optional[datetime] = Query(None),
):
    return await models.workpiece.list_workpiece(credentials, before, after, id, project, batch, status, note_user,
                                                 note_text, note_before, note_after)


@router.patch("/{id}", response_model=models.common.PatchResponse, x_properties=dict(object="workpiece", action="patch"))
async def patch_workpiece(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/workpiece/{id}")),
    id: str = Path(...),
    patch: models.workpiece.WorkpiecePatchBody = Body(...),
):
    return await models.workpiece.patch_workpiece(credentials, id, patch)
