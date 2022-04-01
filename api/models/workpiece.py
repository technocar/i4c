from datetime import datetime
from textwrap import dedent
from typing import List, Optional
from pydantic import root_validator, Field
from common import I4cBaseModel, DatabaseConnection, write_debug_sql, CredentialsAndFeatures
from common.db_tools import get_user_customer
from common.exceptions import I4cClientError
from models import WorkpieceStatusEnum
from models.common import PatchResponse
import common.db_helpers

class NoteAdd(I4cBaseModel):
    """Workpiece comment. Input."""
    user: str = Field(..., title="Commenter.")
    timestamp: datetime = Field(..., title="Timestamp.")
    text: str = Field(..., title="Comment text.")


class Note(NoteAdd):
    """Workpiece comment."""
    note_id: int = Field(..., title="Identifier.")
    user_name: str = Field(..., title="Commenter's name.")
    deleted: bool = Field(..., title="Deleted.")


class Log(I4cBaseModel):
    """Workpiece manufacturing log item."""
    ts: datetime = Field(..., title="Timestamp.")
    seq: int = Field(..., title="Sequence.")
    data: str = Field(..., title="Event or condition type.")
    text: Optional[str] = Field(..., title="Event or condition data.")


class File(I4cBaseModel):
    """
    Files collected during manufacturing. Downloadable via the intfiles
    interface. The version is always 1.
    """
    download_name: str


class Workpiece(I4cBaseModel):
    """Workpiece. Combined from the log and user recorded data."""
    id: Optional[str] = Field(None, title="Identifier.")
    project: Optional[str] = Field(None, title="Project inferred from the log.")
    batch: Optional[str] = Field(None, title="Assigned to batch.")
    status: Optional[WorkpieceStatusEnum] = Field(None, title="Status, manually set or from the log.")
    notes: List[Note] = Field(None, title="User supplied comments.")
    log: List[Log] = Field(None, title="Events and conditions collected from the machine log.")
    files: List[File] = Field(None, title="Files collected during manufacturing.")
    begin_timestamp: Optional[datetime] = Field(None, title="Manufacturing start time.")
    end_timestamp: Optional[datetime] = Field(None, title="Manufacturing end time.")


class WorkpiecePatchCondition(I4cBaseModel):
    """Conditions to check before a change is carried out to a workpiece."""
    flipped: Optional[bool] = Field(False, title="Pass if the condition does not hold.")
    batch: Optional[str] = Field(None, title="Assigned to batch.")
    has_batch: Optional[bool] = Field(None, title="Not assigned to any batches.")
    status: Optional[List[WorkpieceStatusEnum]] = Field(None, title="Has any of the statuses.")

    def match(self, workpiece:Workpiece):
        r = (
                ((self.batch is None) or (self.batch == workpiece.batch))
                and ((self.has_batch is None) or ((workpiece.batch is None) != self.has_batch))
                and ((self.status is None) or (workpiece.status in self.status))
        )
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class WorkpiecePatchChange(I4cBaseModel):
    """Change to a workpiece."""
    batch: Optional[str] = Field(None, title="Assign to batch.")
    delete_batch: Optional[bool] = Field(None, title="Remove from batch.")
    status: Optional[WorkpieceStatusEnum] = Field(None, title="Set status.")
    remove_status: Optional[bool] = Field(False, title="remove manual status.")
    add_note: Optional[List[NoteAdd]] = Field(None, title="Add notes.")
    delete_note: Optional[List[int]] = Field(None, title="Mark notes deleted.")

    def is_empty(self):
        return (self.status is None
                and (self.remove_status is None or not self.remove_status)
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
    """Update to a workpiece. Conditions are evaluated, and if all match, the change is carried out."""
    conditions: List[WorkpiecePatchCondition] = Field(..., title="Conditions to check before the change.")
    change: WorkpiecePatchChange = Field(..., title="Change to be carried out.")


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


workpiece_list_log_detail = open("models/workpiece_list_log_detail.sql").read()


async def get_workpiece_log(begin_timestamp, begin_sequence, end_timestamp, end_sequence, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        write_debug_sql("workpiece_log.sql", workpiece_list_log_detail, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        dr = await conn.fetch(workpiece_list_log_detail, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        res = []
        for r in dr:
            res.append(Log(**r))
        return res


workpiece_list_log_files = open("models/workpiece_list_log_files.sql").read()


async def get_workpiece_files(begin_timestamp, begin_sequence, end_timestamp, end_sequence, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        write_debug_sql("workpiece_files.sql", workpiece_list_log_files, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        dr = await conn.fetch(workpiece_list_log_files, begin_timestamp, begin_sequence, end_timestamp, end_sequence)
        res = []
        for r in dr:
            res.append(File(**r))
        return res


workpiece_list_log_sql = open("models/workpiece_list_log.sql").read()
workpiece_list_log_sql_id = open("models/workpiece_list_log_id.sql").read()


async def list_workpiece(credentials: CredentialsAndFeatures,
                         before=None, after=None, id=None, project=None, project_mask=None,
                         batch=None, batch_mask=None, status=None, note_user=None, note_text=None, note_text_mask=None,
                         note_before=None, note_after=None, with_details=True, with_deleted=False, *, pconn=None):
    sql = workpiece_list_log_sql
    async with DatabaseConnection(pconn) as conn:
        customer = await get_user_customer(credentials.user_id, pconn=conn)
        params = [before, after]
        if id is not None:
            sql = workpiece_list_log_sql_id
            params.append(id)
        if customer is not None:
            params.append(customer)
            sql += f"and res.customer = ${len(params)}\n"
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
                raise I4cClientError("Workpiece not found")
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

            if patch.change.status or patch.change.batch or patch.change.delete_batch or patch.change.remove_status:
                sql_check_db = "select * from workpiece where id = $1"
                dbr = await conn.fetchrow(sql_check_db, id)
                params = [id]
                sql_update = "update workpiece\nset\n"
                sql_insert_fields = "id"
                sql_insert_params = "$1"
                sep = ""
                if patch.change.status or patch.change.remove_status:
                    new_status = patch.change.status if patch.change.status else None
                    params.append(new_status)
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
