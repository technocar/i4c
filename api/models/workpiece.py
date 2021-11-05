from datetime import datetime
from textwrap import dedent
from typing import List, Optional
from common import I4cBaseModel, DatabaseConnection, write_debug_sql
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
    id: Optional[str]
    project: Optional[str]
    batch: Optional[str]
    status: Optional[WorkpieceStatusEnum]
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
        write_debug_sql("workpiece_notes.sql", sql, id)
        dr = await conn.fetch(sql, id)
        res = []
        for r in dr:
            res.append(Note(user=r["user"], timestamp=r["timestamp"], text=r["text"], note_id=r["id"], deleted=r["deleted"]))
        return res


workpiece_list_log_detail = open("models\\workpiece_list_log_detail.sql").read()


async def get_workpiece_log(begin_timestamp, begin_sequence, end_timestamp, end_sequence, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        write_debug_sql("workpiece_log.sql", workpiece_list_log_detail, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        dr = await conn.fetch(workpiece_list_log_detail, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        res = []
        for r in dr:
            res.append(Log(**r))
        return res


workpiece_list_log_files = open("models\\workpiece_list_log_files.sql").read()


async def get_workpiece_files(begin_timestamp, begin_sequence, end_timestamp, end_sequence, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        write_debug_sql("workpiece_files.sql", workpiece_list_log_files, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        dr = await conn.fetch(workpiece_list_log_files, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        res = []
        for r in dr:
            res.append(File(**r))
        return res


workpiece_list_log_sql = open("models\\workpiece_list_log.sql").read()


async def list_workpiece(credentials, before=None, after=None, id=None, project=None, batch=None, status=None,
                         note_user=None, note_text=None, note_before=None, note_after=None, with_details=True, *, pconn=None):
    sql = workpiece_list_log_sql
    async with DatabaseConnection(pconn) as conn:
        params = [before, after]
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}\n"
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
        write_debug_sql("list_workpiece.sql", sql, *params)
        dr = await conn.fetch(sql, *params)
        res = []
        for r in dr:
            d = dict(**r)
            d["notes"] = (await get_workpiece_notes(r["id"], pconn=conn)) if with_details else []
            dpar = (r["begin_timestamp"],r["begin_sequence"], r["end_timestamp"], r["end_sequence"])
            d["log"] = (await get_workpiece_log(*dpar, pconn=conn)) if with_details else []
            d["files"] = (await get_workpiece_files(*dpar, pconn=conn)) if with_details else []
            res.append(Workpiece(**d))
        return res



async def patch_workpiece(credentials, id, patch):
    # todo 1: **********
    pass
