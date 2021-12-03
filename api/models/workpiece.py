from datetime import datetime
from textwrap import dedent
from typing import List, Optional

from fastapi import HTTPException
from pydantic import root_validator

from common import I4cBaseModel, DatabaseConnection, write_debug_sql
from models import WorkpieceStatusEnum
from models.common import PatchResponse
import common.db_helpers


class NoteAdd(I4cBaseModel):
    user: str
    timestamp: datetime
    text: str


class Note(NoteAdd):
    note_id: int
    user_name: str
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
    begin_timestamp: Optional[datetime]
    end_timestamp: Optional[datetime]


class WorkpiecePatchCondition(I4cBaseModel):
    flipped: Optional[bool]
    batch: Optional[str]
    empty_batch: Optional[bool]
    status: Optional[List[WorkpieceStatusEnum]]

    def match(self, workpiece:Workpiece):
        r = (
                ((self.batch is None) or (self.batch == workpiece.batch))
                and ((self.empty_batch is None) or ((workpiece.batch is None) == self.empty_batch))
                and ((self.status is None) or (workpiece.status in self.status))
        )
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class WorkpiecePatchChange(I4cBaseModel):
    batch: Optional[str]
    delete_batch: Optional[bool]
    status: Optional[WorkpieceStatusEnum]
    add_note: Optional[List[NoteAdd]]
    delete_note: Optional[List[int]]

    def is_empty(self):
        return (self.status is None
                and self.batch is None
                and self.delete_batch is None
                and not self.add_note
                and not self.delete_note)

    @root_validator
    def check_exclusive(cls, values):
        batch, delete_batch = values.get('batch'), values.get('delete_batch')
        if batch is not None and delete_batch:
            raise ValueError('batch and delete_batch are exclusive')
        return values


class WorkpiecePatchBody(I4cBaseModel):
    conditions: List[WorkpiecePatchCondition]
    change: WorkpiecePatchChange


async def get_workpiece_notes(id, with_deleted=False, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        sql = dedent("""\
                select 
                  wn.*, 
                  u.name as user_name
                from workpiece_note wn
                join "user" u on u.id = wn."user" 
                where wn.workpiece = $1""")
        if not with_deleted:
            sql += "and wn.deleted = false"
        write_debug_sql("workpiece_notes.sql", sql, id)
        dr = await conn.fetch(sql, id)
        res = []
        for r in dr:
            res.append(Note(user=r["user"], user_name=r["user_name"], timestamp=r["timestamp"],
                            text=r["text"], note_id=r["id"], deleted=r["deleted"]))
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
workpiece_list_log_sql_id = open("models\\workpiece_list_log_id.sql").read()


async def list_workpiece(credentials, before=None, after=None, id=None, project=None, project_mask=None,
                         batch=None, batch_mask=None, status=None, note_user=None, note_text=None, note_text_mask=None,
                         note_before=None, note_after=None, with_details=True, with_deleted=False, *, pconn=None):
    sql = workpiece_list_log_sql
    async with DatabaseConnection(pconn) as conn:
        params = [before, after]
        if id is not None:
            sql = workpiece_list_log_sql_id
            params.append(id)
        if project is not None:
            params.append(project)
            sql += f"and res.project = ${len(params)}\n"
        if project_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(project_mask, "res.project", params)
        if batch is not None:
            params.append(batch)
            sql += f"and res.batch = ${len(params)}\n"
        if batch_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(batch_mask, "res.batch", params)
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
            if note_text_mask is not None:
                sql += "and " + common.db_helpers.filter2sql(note_text_mask, "wn.\"text\"", params)
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
            d["notes"] = (await get_workpiece_notes(r["id"], with_deleted=with_deleted, pconn=conn)) if with_details else []
            dpar = (r["begin_timestamp"],r["begin_sequence"], r["end_timestamp"], r["end_sequence"])
            d["log"] = (await get_workpiece_log(*dpar, pconn=conn)) if with_details else []
            d["files"] = (await get_workpiece_files(*dpar, pconn=conn)) if with_details else []
            res.append(Workpiece(**d))
        return res



async def patch_workpiece(credentials, id, patch: WorkpiecePatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            workpiece = await list_workpiece(credentials, id=id, pconn=conn, with_details=False)
            if len(workpiece) == 0:
                raise HTTPException(status_code=400, detail="Workpiece not found")
            workpiece = workpiece[0]

            match = True
            for cond in patch.conditions:
                match = cond.match(workpiece)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)

            if patch.change.status or patch.change.batch or patch.change.delete_batch:
                sql_check_db = "select * from workpiece where id = $1"
                dbr = await conn.fetchrow(sql_check_db, id)
                params = [id]
                sql_update = "update workpiece\nset\n"
                sql_insert_fields = "id"
                sql_insert_params = "$1"
                sep = ""
                if patch.change.status:
                    params.append(patch.change.status)
                    sql_update += f"{sep}\"manual_status\"=${len(params)}"
                    sql_insert_fields += ", manual_status"
                    sql_insert_params += f", ${len(params)}"
                    sep = ",\n"
                if patch.change.batch:
                    params.append(patch.change.batch)
                    sql_update += f"{sep}\"batch\"=${len(params)}"
                    sql_insert_fields += ", batch"
                    sql_insert_params += f", ${len(params)}"
                    sep = ",\n"
                if patch.change.delete_batch:
                    sql_update += f"{sep}\"batch\"=null"
                    sep = ",\n"
                sql_update += "\nwhere id = $1"
                sql_insert = f"insert into workpiece ({sql_insert_fields}) values ({sql_insert_params})\n"
                if dbr:
                    await conn.execute(sql_update, *params)
                else:
                    await conn.execute(sql_insert, *params)

            if patch.change.delete_note:
                for d in patch.change.delete_note:
                    sql = "update workpiece_note set deleted=true where id = $1"
                    await conn.execute(sql, d)

            if patch.change.add_note:
                for a in patch.change.add_note:
                    sql = "insert into workpiece_note (workpiece, \"user\", \"timestamp\", \"text\")" \
                          "values ($1, $2, $3, $4)"
                    await conn.execute(sql, id, a.user, a.timestamp, a.text)

            return PatchResponse(changed=True)
