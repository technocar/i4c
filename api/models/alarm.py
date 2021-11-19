import math
import textwrap
from datetime import datetime, timedelta
from enum import Enum
from textwrap import dedent
from typing import List, Optional

from fastapi import HTTPException
from pydantic import Field, root_validator

import common.db_helpers
from common.debug_helpers import debug_print
from common.exceptions import I4cInputValidationError
from common import I4cBaseModel, DatabaseConnection, write_debug_sql, series_intersect
from models import CommonStatusEnum
from models.common import PatchResponse
from fractions import Fraction


class AlarmCondLogRowCategory(str, Enum):
    sample = "SAMPLE"
    event = "EVENT"
    condition = "CONDITION"


class AlarmCondSampleAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1th"
    q4th = "q4th"
    slope = "slope"


class AlarmCondSampleAggSlopeKind(str, Enum):
    time = "time"
    position = "position"


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

    def __eq__(self, other):
        if not isinstance(other, AlarmCondSample):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.aggregate_period == other.aggregate_period)
                and (self.aggregate_count == other.aggregate_count)
                and (self.aggregate_method == other.aggregate_method)
                and (self.rel == other.rel)
                and (self.value == other.value))

    async def insert_to_db(self, alarm_id, conn):
        sql_insert = dedent("""\
            insert into alarm_cond (alarm, log_row_category, device, 
                                    data_id, aggregate_period, aggregate_count, 
                                    aggregate_method, rel, value_num
                                   ) values ($1, $2, $3,
                                             $4, $5, $6,
                                             $7, $8, $9)
            returning id
            """)
        await conn.fetchrow(sql_insert, alarm_id, AlarmCondLogRowCategory.sample, self.device,
                            self.data_id, self.aggregate_period, self.aggregate_count,
                            self.aggregate_method, self.rel, self.value)


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
    id: int
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


class AlarmEventCheckResult(I4cBaseModel):
    alarm: str
    alarmevent_count: Optional[int]


class AlarmRecipientStatus(str, Enum):
    outbox = "outbox"
    sent = "sent"
    deleted = "deleted"

async def alarmdef_get(credentials, name, *, pconn=None) -> Optional[AlarmDef]:
    async with DatabaseConnection(pconn) as conn:
        sql_alarm = dedent("""\
                           select 
                             "id", "name", max_freq, last_check, last_report
                           from "alarm"
                           where "name" = $1
                           """)
        idr = await conn.fetchrow(sql_alarm, name)
        if not idr:
            return None

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

        return AlarmDef(id=idr["id"],
                        name=idr["name"],
                        conditions=conds,
                        max_freq=idr["max_freq"],
                        last_check=idr["last_check"],
                        last_report=idr["last_report"]
                        )


async def alarmdef_put(credentials, name, alarm: AlarmDefIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            old_alarm = await alarmdef_get(credentials, name, pconn=conn)
            new_last_check = datetime.now()
            if old_alarm is None:
                sql_insert = dedent("""\
                    insert into alarm (name, max_freq, last_check) values ($1, $2, $3)
                    returning id
                    """)
                alarm_id = (await conn.fetchrow(sql_insert, name, alarm.max_freq, new_last_check))[0]
                old_alarm = AlarmDef(
                        id=alarm_id,
                        name=name,
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
                await c.insert_to_db(old_alarm.id, conn)

            new_alarm = await alarmdef_get(credentials, name, pconn=conn)
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
            d = await alarmdef_get(credentials, r[0], pconn=conn)
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

alarm_check_load_sql = open("models\\alarm_check_load.sql").read()


def prev_iterator(iterable, *, include_first=True):
    prev = None
    include_next = include_first
    for current in iterable:
        if include_next:
            yield prev, current
        include_next = True
        prev = current


def check_rel(rel, left, right):
    if left is None:
        return False
    if right is None:
        return False
    if rel == "=":
        return left == right
    if rel == "!=":
        return left != right
    if rel == "*":
        return left in right
    if rel == "!*":
        return left not in right
    if rel == "<":
        return left < right
    if rel == "<=":
        return left <= right
    if rel == ">":
        return left > right
    if rel == ">=":
        return left >= right
    return False


def frac_index(list, index):
    i = math.floor(index)
    x = Fraction(index - i).limit_denominator()
    if x == 0:
        return list[i]
    return float(list[i]*(1-x) + list[i+1]*x)


def calc_aggregate(method, agg_values, slope_kind: AlarmCondSampleAggSlopeKind):
    agg_values = [v for v in agg_values if v["value_num"] is not None]
    if not agg_values:
        return None
    if method == AlarmCondSampleAggMethod.avg:
        return sum(v["value_num"] for v in agg_values) / len(agg_values)
    elif method in (AlarmCondSampleAggMethod.median, AlarmCondSampleAggMethod.q1st, AlarmCondSampleAggMethod.q4st):
        o = sorted(v["value_num"] for v in agg_values)
        if method == AlarmCondSampleAggMethod.median:
            return frac_index(o, (len(o) - 1) / 2)
        elif method == AlarmCondSampleAggMethod.q1st:
            return frac_index(o, (len(o) - 1) / 4)
        elif method == AlarmCondSampleAggMethod.q4th:
            return frac_index(o, (len(o) - 1) * 3 / 4)
    elif method == AlarmCondSampleAggMethod.slope:
        n = len(agg_values)
        if n == 1:
            return 0
        xl = []
        if slope_kind == AlarmCondSampleAggSlopeKind.time:
            xl = [(v["timestamp"] - agg_values[0]["timestamp"]).total_seconds() for v in agg_values]
        elif slope_kind == AlarmCondSampleAggSlopeKind.position:
            xl = range(len(agg_values))
        yl = [v["value_num"] for v in agg_values]
        # https://www.statisticshowto.com/probability-and-statistics/regression-analysis/find-a-linear-regression-equation/
        return ( (n * sum(x * y for x, y in zip(xl, yl)) - sum(xl) * sum(yl))
                 / (n * sum(x ** 2 for x in xl) - sum(xl)**2))


async def check_alarmevent(credentials, alarm, max_count, *, override_last_check=None, override_now=None):
    res = []
    param_now = datetime.now() if override_now is None else override_now
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql_alarm = "select * from alarm\n"\
                        "where (max_freq is null or last_report is null or ($1 > last_report + max_freq * interval '1 second'))"
            params = [param_now]
            if alarm is not None:
                params.append(alarm)
                sql_alarm += f"and id = ${len(alarm)}\n"
            if max_count is not None:
                params.append(override_last_check)
                sql_alarm += f"order by ($1 - coalesce(${len(alarm)}, last_check)) / nullif(max_freq,0) desc, last_check asc\n"
            db_alarm = await conn.fetch(sql_alarm, *params)
            for row_alarm_recno, row_alarm in enumerate(db_alarm, start=1):
                if max_count is not None and row_alarm_recno > max_count:
                    break

                last_check = row_alarm["last_check"] if override_last_check is None else override_last_check

                sql_cond = "select * from alarm_cond where alarm = $1 order by log_row_category" # cond/ev/sample order
                db_conds = await conn.fetch(sql_cond, row_alarm["id"])
                total_series = None
                for row_cond_recno, row_cond in enumerate(db_conds, start=1):
                    last_check_mod = last_check
                    if total_series is not None and row_cond["log_row_category"] == AlarmCondLogRowCategory.sample:
                        last_check_mod = min((i for i in (last_check_mod, total_series[0].start) if i is not None), default=None)
                    write_debug_sql(f"alarm_check_load_series_{row_alarm_recno}_{row_cond_recno}.sql",
                                    alarm_check_load_sql, row_cond["device"], row_cond["data_id"], last_check_mod, param_now)
                    db_series = await conn.fetch(alarm_check_load_sql, row_cond["device"], row_cond["data_id"], last_check_mod, param_now)
                    current_series = series_intersect.Series()
                    agg_values = []
                    for r_series_prev, r_series in prev_iterator(db_series, include_first=False):
                        if row_cond["log_row_category"] == AlarmCondLogRowCategory.condition:
                            if check_rel("=", row_cond["value_text"], r_series_prev["value_text"]):
                                age_min = timedelta(seconds=row_cond["age_min"] if row_cond["age_min"] else 0)
                                if r_series_prev["timestamp"] + age_min < r_series["timestamp"]:
                                    t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min, r_series["timestamp"],
                                                                    f'{row_cond["device"]} {row_cond["data_id"]} {row_cond["value_text"]}'
                                                                    )
                                current_series.add(t)
                        elif row_cond["log_row_category"] == AlarmCondLogRowCategory.event:
                            if check_rel(row_cond["rel"], row_cond["value_text"], r_series_prev["value_text"]):
                                age_min = timedelta(seconds=row_cond["age_min"] if row_cond["age_min"] else 0)
                                age_max = timedelta(seconds=row_cond["age_max"] if row_cond["age_max"] else 0)
                                if r_series_prev["timestamp"] + age_min < r_series["timestamp"] - age_max:
                                    t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min, r_series["timestamp"] - age_max,
                                                                    f'{row_cond["device"]} {row_cond["data_id"]} '
                                                                    f'{r_series_prev["value_text"]}       ({row_cond["rel"]} {row_cond["value_text"]})')
                                current_series.add(t)
                        elif row_cond["log_row_category"] == AlarmCondLogRowCategory.sample:
                            if not total_series.is_timestamp_in(r_series_prev["timestamp"]):
                                continue
                            aggregated_value = None
                            if row_cond["aggregate_period"]:
                                agg_time_len = (r_series["timestamp"] - agg_values[0]["timestamp"]).total_seconds() if len(agg_values) > 0 else 0
                                if agg_time_len >= row_cond["aggregate_period"]:
                                    aggregated_value = calc_aggregate(row_cond["aggregate_method"], agg_values, AlarmCondSampleAggSlopeKind.time)
                                agg_values.append(r_series)
                                while (r_series["timestamp"] - agg_values[0]["timestamp"]).total_seconds() > row_cond["aggregate_period"]:
                                    del agg_values[0]
                            if row_cond["aggregate_count"]:
                                if len(agg_values) == row_cond["aggregate_count"]:
                                    aggregated_value = calc_aggregate(row_cond["aggregate_method"], agg_values, AlarmCondSampleAggSlopeKind.position)
                                    del agg_values[0]
                                agg_values.append(r_series)

                            debug_print(aggregated_value)
                            if check_rel(row_cond["rel"], aggregated_value, row_cond["value_num"]):
                                t = series_intersect.TimePeriod(r_series_prev["timestamp"], r_series["timestamp"],
                                                                f'{row_cond["device"]} {row_cond["data_id"]} '
                                                                f'{aggregated_value}       ({row_cond["rel"]} {row_cond["value_num"]})')
                                current_series.add(t)

                    debug_print(f"current_series ({row_cond_recno}):")
                    debug_print(current_series)
                    if total_series is None:
                        total_series = current_series
                    else:
                        total_series = series_intersect.Series.intersect(total_series, current_series)
                    if len(total_series) == 0:
                        break
                    debug_print(f"total_series ({row_cond_recno}):")
                    debug_print(total_series)

                sql_update_alarm = "update alarm set last_check = $2"

                if total_series is not None and len(total_series) > 0:
                    res.append(AlarmEventCheckResult(alarm=row_alarm["name"], alarmevent_count=len(total_series)))
                    sql_insert = dedent("""\
                        insert into alarm_event (alarm, created, summary, description) 
                        values ($1, now(), $2, $3)
                        returning id
                        """)
                    summary = f'{row_alarm["name"]}   {total_series[0].start} - {total_series[-1].end}'
                    description = "\n\n".join(f'{s.start} - {s.end}\n{textwrap.indent(s.extra, " - ")}' for s in total_series)
                    alarm_event_id = (await conn.fetchrow(sql_insert, row_alarm["id"], summary, description))[0]

                    subs = await conn.fetch("select * from alarm_sub where alarm = $1", row_alarm["id"])
                    for sub in subs:
                        sql_r = 'insert into alarm_recipient (event, "user", method, address, "status") values ($1, $2, $3, $4, $5)'
                        await conn.execute(sql_r, alarm_event_id, sub["user"], sub["method"], sub["address"], AlarmRecipientStatus.outbox)
                    sql_update_alarm += ", last_report = $2"
                sql_update_alarm += "where id = $1"
                await conn.execute(sql_update_alarm, row_alarm["id"], param_now)

    return res
