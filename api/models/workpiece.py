from datetime import datetime
from typing import List, Optional
from common import I4cBaseModel
from models import WorkpieceStatusEnum


class NoteAdd(I4cBaseModel):
    user: str
    timestamp: datetime
    text: str


class Note(NoteAdd):
    note_id: int
    deleted: bool


class Log(I4cBaseModel):
    ts: datetime
    seq: int
    data: str
    text: str


class File(I4cBaseModel):
    id: str
    download_name: str


class Workpiece(I4cBaseModel):
    id: str
    project: str
    batch: Optional[str]
    status: WorkpieceStatusEnum
    notes: List[Note]
    log: List[Log]
    files: List[File]


class WorkpiecePatchCondition(I4cBaseModel):
    batch: Optional[str]
    status: Optional[WorkpieceStatusEnum]

    def match(self, workpiece:Workpiece):
        return (
                ((self.batch is None) or (self.batch == workpiece.batch))
                and ((self.status is None) or (self.status == workpiece.status))
        )


class WorkpiecePatchChange(I4cBaseModel):
    batch: Optional[str]
    status: Optional[WorkpieceStatusEnum]
    add_note: Optional[List[NoteAdd]]
    delete_note: Optional[List[str]]

    def is_empty(self):
        return (self.status is None
                and self.status is None
                and not self.add_note
                and not self.delete_note)


class WorkpiecePatchBody(I4cBaseModel):
    conditions: List[WorkpiecePatchCondition]
    change: WorkpiecePatchChange


async def get_workpiece(credentials, id):
    # todo 1: **********
    pass


async def list_workpiece(credentials, before, after, id, project, batch, status, note_user,
                         note_text, note_before, note_after):
    # todo 1: **********
    pass


async def patch_workpiece(credentials, id, patch):
    # todo 1: **********
    pass
