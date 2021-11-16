from datetime import datetime
from enum import Enum
from textwrap import dedent
from typing import List, Optional

from fastapi import HTTPException
from pydantic import Field, root_validator

import common.db_helpers
from common.exceptions import I4cInputValidationError
from common import I4cBaseModel, DatabaseConnection, write_debug_sql
from models import CommonStatusEnum
from models.common import PatchResponse


class AlarmCondLogRowCategory(str, Enum):
    sample = "sample"
    event = "event"
    condition = "condition"


class AlarmCondSampleAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1th"
    q4th = "q4th"
    slope = "slope"


class AlarmCondSampleRel(str, Enum):
    eq = "="
    neq = "!="
    less = "<"
    leq = "<="
    gtr = ">"
    geq = ">="


class AlarmCondSample(I4cBaseModel):
    device: str
    data_id: str
    aggregate_period: Optional[float] = Field(None, description="sec")
    aggregate_count: Optional[int]
    aggregate_method: AlarmCondSampleAggMethod
    rel: AlarmCondSampleRel
    value: float
    age_min: Optional[float] = Field(None, description="sec")
    age_max: Optional[float] = Field(None, description="sec")

    def __eq__(self, other):
        if not isinstance(other, AlarmCondSample):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.aggregate_period == other.aggregate_period)
                and (self.aggregate_count == other.aggregate_count)
                and (self.aggregate_method == other.aggregate_method)
                and (self.rel == other.rel)
                and (self.value == other.value)
                and (self.age_min == other.age_min)
                and (self.age_max == other.age_max))

    async def insert_to_db(self, alarm_id, conn):
        sql_insert = dedent("""\
            insert into alarm_cond (alarm, log_row_category, device, 
                                    data_id, aggregate_period, aggregate_count, 
                                    aggregate_method, rel, value_num, 
                                    age_min, age_max
                                   ) values ($1, $2, $3,
                                             $4, $5, $6,
                                             $7, $8, $9,
                                             $10, $11)
            returning id
            """)
        await conn.fetchrow(sql_insert, alarm_id, AlarmCondLogRowCategory.sample, self.device,
                            self.data_id, self.aggregate_period, self.aggregate_count,
                            self.aggregate_method, self.rel, self.value,
                            self.age_min, self.age_max)


    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('aggregate_period') is not None else 0
        x += 1 if values.get('aggregate_count') is not None else 0
        if x > 1:
            raise I4cInputValidationError('aggregate_period and aggregate_count are exclusive')
        if x == 0:
            raise I4cInputValidationError('aggregate_period or aggregate_count are required')
        return values



class AlarmCondEventRel(str, Enum):
    eq = "="
    neq = "!="
    contains = "*"
    not_contains = "!*"


class AlarmCondEvent(I4cBaseModel):
    device: str
    data_id: str
    rel: AlarmCondEventRel
    value: str
    age_min: Optional[float] = Field(None, description="sec")
    age_max: Optional[float] = Field(None, description="sec")

    def __eq__(self, other):
        if not isinstance(other, AlarmCondEvent):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.rel == other.rel)
                and (self.value == other.value)
                and (self.age_min == other.age_min)
                and (self.age_max == other.age_max))

    async def insert_to_db(self, alarm_id, conn):
        sql_insert = dedent("""\
            insert into alarm_cond (alarm, log_row_category, device, 
                                    data_id, rel, value_text, 
                                    age_min, age_max
                                   ) values ($1, $2, $3,
                                             $4, $5, $6,
                                             $7, $8)
            returning id
            """)
        await conn.fetchrow(sql_insert, alarm_id, AlarmCondLogRowCategory.event, self.device,
                            self.data_id, self.rel, self.value,
                            self.age_min, self.age_max)


class AlarmCondCondition(I4cBaseModel):
    device: str
    data_id: str
    value: str
    age_min: Optional[float] = Field(None, description="sec")

    def __eq__(self, other):
        if not isinstance(other, AlarmCondCondition):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.value == other.value)
                and (self.age_min == other.age_min))

    async def insert_to_db(self, alarm_id, conn):
        sql_insert = dedent("""\
            insert into alarm_cond (alarm, log_row_category, device, 
                                    data_id, value_text, age_min
                                   ) values ($1, $2, $3,
                                             $4, $5, $6)
            returning id
            """)
        await conn.fetchrow(sql_insert, alarm_id, AlarmCondLogRowCategory.condition, self.device,
                            self.data_id, self.value, self.age_min)


class AlarmCond(I4cBaseModel):
    sample: Optional[AlarmCondSample]
    event: Optional[AlarmCondEvent]
    condition: Optional[AlarmCondCondition]

    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('sample') is not None else 0
        x += 1 if values.get('event') is not None else 0
        x += 1 if values.get('condition') is not None else 0
        if x > 1:
            raise I4cInputValidationError('sample, event, and condition are exclusive')
        if x == 0:
            raise I4cInputValidationError('sample, event, or condition are required')
        return values

    def __eq__(self, other):
        if not isinstance(other, AlarmCond):
            return False
        return ((self.sample == other.sample)
                and (self.event == other.event)
                and (self.condition == other.condition))


    async def insert_to_db(self, alarm_id, conn):
        if self.sample:
            await self.sample.insert_to_db(alarm_id, conn)
        if self.event:
            await self.event.insert_to_db(alarm_id, conn)
        if self.condition:
            await self.condition.insert_to_db(alarm_id, conn)


class AlarmCondId(AlarmCond):
    id: int


class AlarmDefIn(I4cBaseModel):
    conditions: List[AlarmCond]
    max_freq: Optional[float] = Field(None, description="sec")


class AlarmDef(AlarmDefIn):
    name: str
    last_check: datetime
    last_report: Optional[datetime]


class AlarmMethod(str, Enum):
    email = "email"
    push = "push"
    none = "none"


class AlarmSubIn(I4cBaseModel):
    alarm: int
    seq: int
    user: Optional[str]
    method: AlarmMethod
    address: Optional[str]
    status: CommonStatusEnum


class AlarmSub(AlarmSubIn):
    id: int
    alarm_name: str
    user_name: Optional[str]


class AlarmSubPatchCondition(I4cBaseModel):
    flipped: Optional[bool]
    status: Optional[CommonStatusEnum]
    address: Optional[str]
    empty_address: Optional[bool]

    def match(self, alarmsub:AlarmSub):
        r = (((self.status is None) or (alarmsub.status == self.status))
             and ((self.address is None) or (self.address == alarmsub.address))
             and ((self.empty_address is None) or (bool(alarmsub.address) != self.empty_address)))

        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class AlarmSubPatchChange(I4cBaseModel):
    status: Optional[CommonStatusEnum]
    address: Optional[str]
    clear_address: Optional[bool]

    def is_empty(self):
        return self.status is None \
               and self.address is None \
               and (self.clear_address is None or not self.clear_address)

    @root_validator
    def check_exclusive(cls, values):
        address, clear_address = values.get('address'), values.get('clear_address')
        if address is not None and clear_address:
            raise ValueError('address and clear_address are exclusive')
        return values


class AlarmSubPatchBody(I4cBaseModel):
    conditions: List[AlarmSubPatchCondition]
    change: AlarmSubPatchChange


async def alarmdef_get(credentials, name, *, pconn=None) -> (int, AlarmDef):
    async with DatabaseConnection(pconn) as conn:
        sql_alarm = dedent("""\
                           select 
                             "id", "name", max_freq, last_check, last_report
                           from "alarm"
                           where "name" = $1
                           """)
        idr = await conn.fetchrow(sql_alarm, name)
        if not idr:
            return None, None

        sql_alarm_cond = dedent("""\
                                    select 
                                        id,
                                        alarm,
                                        log_row_category,
                                       
                                        device,
                                        data_id,
                                        aggregate_period,
                                        aggregate_count,
                                        aggregate_method,
                                        rel,
                                        value_num,
                                        value_text,
                                        age_min,
                                        age_max
                                    from "alarm_cond"
                                    where "alarm" = $1
                                """)
        conds = []
        for r in await conn.fetch(sql_alarm_cond, idr["id"]):
            if r["log_row_category"] == AlarmCondLogRowCategory.sample:
                conds.append(AlarmCondId(id=r["id"],
                                         sample=AlarmCondSample(device=r["device"],
                                                                data_id=r["data_id"],
                                                                aggregate_period=r["aggregate_period"],
                                                                aggregate_count=r["aggregate_count"],
                                                                aggregate_method=r["aggregate_method"],
                                                                rel=r["rel"],
                                                                value=r["value_num"],
                                                                age_min=r["age_min"],
                                                                age_max=r["age_max"])))
            if r["log_row_category"] == AlarmCondLogRowCategory.event:
                conds.append(AlarmCondId(id=r["id"],
                                         event=AlarmCondEvent(device=r["device"],
                                                              data_id=r["data_id"],
                                                              rel=r["rel"],
                                                              value=r["value_text"],
                                                              age_min=r["age_min"],
                                                              age_max=r["age_max"])))
            if r["log_row_category"] == AlarmCondLogRowCategory.condition:
                conds.append(AlarmCondId(id=r["id"],
                                         condition=AlarmCondCondition(device=r["device"],
                                                                      data_id=r["data_id"],
                                                                      value=r["value_text"],
                                                                      age_min=r["age_min"])))

        return (idr["id"],
               AlarmDef(name=idr["name"],
                        conditions=conds,
                        max_freq=idr["max_freq"],
                        last_check=idr["last_check"],
                        last_report=idr["last_report"]
                        ))


async def alarmdef_put(credentials, name, alarm: AlarmDefIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            alarm_id, old_alarm = await alarmdef_get(credentials, name, pconn=conn)
            new_last_check = datetime.now()
            if alarm_id is None:
                sql_insert = dedent("""\
                    insert into alarm (name, max_freq, last_check) values ($1, $2, $3)
                    returning id
                    """)
                alarm_id = (await conn.fetchrow(sql_insert, name, alarm.max_freq, new_last_check))[0]
                old_alarm = AlarmDef(name=alarm_id,
                        conditions=[],
                        max_freq=alarm.max_freq,
                        last_check=new_last_check,
                        last_report=None
                        )
            else:
                sql_update = "update alarm set max_freq = $2, last_check = $3 where name = $1"
                await conn.execute(sql_update, name, alarm.max_freq, new_last_check)
                old_alarm.last_check = new_last_check

            nc = alarm.conditions
            # remove duplicated conditions from list
            nc = [c for i, c in enumerate(nc) if not any(c == cprev for cprev in nc[:i])]

            ins_c = [c for c in nc if not any(c == cother for cother in old_alarm.conditions)]
            del_c = [c for c in old_alarm.conditions if not any(c == cother for cother in nc)]

            for c in del_c:
                assert(isinstance(c, AlarmCondId))
                sql_del = "delete from alarm_cond where id = $1"
                await conn.execute(sql_del, c.id)

            for c in ins_c:
                await c.insert_to_db(alarm_id, conn)

            _, new_alarm = await alarmdef_get(credentials, name, pconn=conn)
            return new_alarm


async def alarmdef_list(credentials, name_mask, report_after, *, pconn=None):
    sql = "select name from \"alarm\" where True\n"
    async with DatabaseConnection(pconn) as conn:
        params = []
        if name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(name_mask, "name", params)
        if report_after is not None:
            params.append(report_after)
            sql += f"and last_report >= ${len(params)}\n"
        alarms = await conn.fetch(sql, *params)

        res = []
        for r in alarms:
            _, d = await alarmdef_get(credentials, r[0], pconn=conn)
            res.append(d)
        return res


async def alarmsub_list(credentials, alarm=None, alarm_name=None, alarm_name_mask=None, seq=None, user=None,
                        user_name=None, user_name_mask=None, method=None, status=None, *, pconn=None) -> List[AlarmSub]:
    sql = dedent("""\
            with res as (
                select
                  als.*,
                  al."name" as alarm_name,
                  u."name" as user_name
                from alarm_sub als
                join alarm al on al.id = als.alarm
                left join "user" u on u.id = als."user"
                )
            select * from res
            where True
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if alarm is not None:
            params.append(alarm)
            sql += f"and res.alarm = ${len(params)}\n"
        if alarm_name is not None:
            params.append(alarm_name)
            sql += f"and res.alarm_name = ${len(alarm_name)}\n"
        if alarm_name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(alarm_name_mask, "res.alarm_name", params)
        if seq is not None:
            params.append(seq)
            sql += f"and res.seq = ${len(params)}\n"
        if user is not None:
            params.append(user)
            sql += f"and res.user = ${len(params)}\n"
        if user_name is not None:
            params.append(user_name)
            sql += f"and res.user_name = ${len(alarm_name)}\n"
        if user_name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(user_name_mask, "res.user_name", params)
        if method is not None:
            params.append(method)
            sql += f"and res.method = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        write_debug_sql("alarmsub_list.sql", sql, *params)
        res = await conn.fetch(sql, *params)
        return [AlarmSub(**dict(r)) for r in res]


async def post_alarmsub(credentials, alarmsub:AlarmSub) -> AlarmSub:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql_check = "select * from alarm_sub where alarm = $1 and seq = $2"
            pre_db = conn.execute(sql_check, alarmsub.alarm, alarmsub.seq)
            if pre_db:
                sql_mod = dedent("""\
                    update alarm_sub
                    set "user" = $3,
                        method = $4,
                        address = $5,
                        status = $6 
                    where alarm = $1 and seq = $2
                    """)
            else:
                sql_mod = "insert into alarm_sub (alarm, seq, \"user\", method, address, status)\n" \
                          "values ($1, $2, $3, $4, $5, $6)"
            conn.execute(sql_mod, alarmsub.alarm, alarmsub.seq, alarmsub.user, alarmsub.method, alarmsub.address, alarmsub.status)
            res = await alarmsub_list(credentials, alarm=alarmsub.alarm, seq=alarmsub.seq)
            return res[0]


async def patch_alarmsub(credentials, alarm, seq, patch: AlarmSubPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            al = await alarmsub_list(credentials, alarm=alarm, seq=seq, pconn=conn)
            if len(al) == 0:
                raise HTTPException(status_code=404, detail="No record found")
            al = al[0]

            match = True
            for cond in patch.conditions:
                match = cond.match(al)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)

            params = [alarm, seq]
            sql = "update alarm_sub\nset\n"
            sep = ""
            if patch.change.status:
                params.append(patch.change.status)
                sql += f"{sep}\"status\"=${len(params)}"
                sep = ",\n"
            if patch.change.address is not None:
                params.append(patch.change.address)
                sql += f"{sep}\"address\"=${len(params)}"
                sep = ",\n"
            if patch.change.clear_address:
                sql += f"{sep}\"address\"= null"
                sep = ",\n"
            sql += "\nwhere alarm = $1::int and seq = $2"
            if len(params) > 2:
                await conn.execute(sql, *params)

            return PatchResponse(changed=True)
