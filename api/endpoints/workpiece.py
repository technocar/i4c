from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Query, Path, Body
import models.workpiece
import models.common
import common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures
from common.exceptions import I4cClientNotFound
from models import WorkpieceStatusEnum

router = I4cApiRouter(include_path="/workpiece")


@router.get("/{id}", response_model=models.workpiece.Workpiece, operation_id="workpiece_get",
            summary="Retrieve workpiece.")
async def get_workpiece(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("get/workpiece/{id}")),
    id: str = Path(...),
    with_deleted: Optional[bool] = Query(False, description="With or without deleted notes")
):
    """Get a workpiece."""
    res = await models.workpiece.list_workpiece(credentials, id=id, with_deleted=with_deleted)
    if len(res) > 0:
        return res[0]
    raise I4cClientNotFound("No record found")


@router.get("", response_model=List[models.workpiece.Workpiece], operation_id="workpiece_list",
            summary="List workpieces.")
async def list_workpiece(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("get/workpiece")),
    before: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
    after: Optional[datetime] = Query(None, description="eg.: 2021-08-15T15:53:11.123456Z"),
    id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    project_mask: Optional[List[str]] = Query(None),
    batch: Optional[str] = Query(None),
    batch_mask: Optional[List[str]] = Query(None),
    status: Optional[WorkpieceStatusEnum] = Query(None),
    note_user: Optional[str] = Query(None),
    note_text: Optional[str] = Query(None),
    note_text_mask: Optional[List[str]] = Query(None),
    note_before: Optional[datetime] = Query(None),
    note_after: Optional[datetime] = Query(None),
    with_details: Optional[bool] = Query(True, description="With or without note, log, and files"),
    with_deleted: Optional[bool] = Query(False, description="With or without deleted notes")
    # todo log???
):
    """List workpieces."""
    return await models.workpiece.list_workpiece(credentials, before, after, id, project, project_mask, batch,
                                                 batch_mask, status, note_user, note_text, note_text_mask, note_before,
                                                 note_after, with_details, with_deleted)


@router.patch("/{id}", response_model=models.common.PatchResponse, operation_id="workpiece_patch",
              summary="Update workpiece.")
async def patch_workpiece(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("patch/workpiece/{id}")),
    id: str = Path(...),
    patch: models.workpiece.WorkpiecePatchBody = Body(...),
):
    """Update a workpiece."""
    return await models.workpiece.patch_workpiece(credentials, id, patch)
