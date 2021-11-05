from datetime import datetime
from textwrap import dedent
from typing import List, Optional
from common import I4cBaseModel, DatabaseConnection
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


async def get_workpiece_notes(id, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = "select * from workpiece_note wn where wn.workpiece = $1"
        dr = await conn.fetch(sql, id)
        res = []
        for r in dr:
            res.append(Note(user=r["user"], timestamp=r["timestamp"], text=r["text"], note_id=r["id"], deleted=r["deleted"]))
        return res


async def list_workpiece(credentials, before=None, after=None, id=None, project=None, batch=None, status=None,
                         note_user=None, note_text=None, note_before=None, note_after=None, *, pconn=None):
    sql = dedent("""\
            with
                res as (
                    select 
                        id, project, batch, status, log_window_begin, log_window_end
                    from workpiece
                )
            select * 
            from res
            where True
            """)
    async with DatabaseConnection(pconn) as conn:
        params = []

        if before is not None:
            params.append(before)
            sql += f"and coalesce(res.log_window_begin, res.log_window_end) <= ${len(params)}\n"
        if after is not None:
            params.append(after)
            sql += f"and coalesce(res.log_window_end, res.log_window_begin) >= ${len(params)}\n"
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}::integer\n"
        if project is not None:
            params.append(project)
            sql += f"and res.project = ${len(params)}\n"
        if batch is not None:
            params.append(batch)
            sql += f"and res.batch = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if note_user is not None or note_text is not None or note_before is not None or note_after is not None:
            sql_note = "select * from workpiece_note wn where wn.workpiece = res.id"
            if note_user is not None:
                params.append(note_user)
                sql += f"and wn.\"user\" = ${len(params)}\n"
            if note_text is not None:
                params.append(note_text)
                sql += f"and wn.\"text\" = ${len(params)}\n"
            if note_before is not None:
                params.append(note_before)
                sql += f"and wn.\"timestamp\" <= ${len(params)}\n"
            if note_after is not None:
                params.append(note_after)
                sql += f"and wn.\"timestamp\" >= ${len(params)}\n"
            sql += f" and exists({sql_note})"
        dr = await conn.fetch(sql, *params)
        res = []
        for r in dr:
            d = dict(**r)
            d["notes"] = await get_workpiece_notes(r["id"], pconn=conn)
            # todo: get **log** and **files** data from table log using `log_window_begin -> log_window_end`
            d["log"] = []
            d["files"] = []
            res.append(Workpiece(**d))
        return res



async def patch_workpiece(credentials, id, patch):
    # todo 1: **********
    pass
