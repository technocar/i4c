import textwrap
from datetime import datetime, timedelta
from enum import Enum
from textwrap import dedent
from typing import List, Optional
from pydantic import Field, root_validator
import common.db_helpers
from common.exceptions import I4cClientError
from common.debug_helpers import debug_print
from common.exceptions import I4cInputValidationError, I4cClientNotFound
from common import I4cBaseModel, DatabaseConnection, write_debug_sql, series_intersect
from common.tools import frac_index
from models import CommonStatusEnum, CondEventRel
from models.common import PatchResponse, series_check_load_sql, check_rel, prev_iterator


async def get_alarm_id(conn, name: str):
    sql = "select id from alarm where name = $1"
    res = await conn.fetchrow(sql, name)
    if res:
        return res[0]
    return None


class AlarmCondLogRowCategory(str, Enum):
    sample = "SAMPLE"
    event = "EVENT"
    condition = "CONDITION"


class AlarmCondSampleAggMethod(str, Enum):
    """
    Aggregation function for numeric values. Q1st and q4th are 1st and 4th quintiles, and slope is linear regression.
    """
    avg = "avg"
    median = "median"
    q1st = "q1st"
    q4th = "q4th"
    slope = "slope"


class AlarmCondSampleAggSlopeKind(str, Enum):
    """Slope calculation x value."""
    time = "time"
    position = "position"


class AlarmCondSampleRel(str, Enum):
    """Relation for numeric values."""
    eq = "eq"
    neq = "neq"
    less = "lt"
    leq = "lte"
    gtr = "gt"
    geq = "gte"

    def nice_value(self):
        map = { AlarmCondSampleRel.eq: "=",
                AlarmCondSampleRel.neq: "!=",
                AlarmCondSampleRel.less: "<",
                AlarmCondSampleRel.leq: "<=",
                AlarmCondSampleRel.gtr: ">",
                AlarmCondSampleRel.geq: ">=" }
        return map[self]

    def values(self):
        return self, self.nice_value()

    @classmethod
    def from_nice_value(cls, nice_value):
        for k in cls:
            k: AlarmCondSampleRel
            if nice_value in k.values():
                return k
        raise Exception(f"`{nice_value}` not found in enum.")


class AlarmCondSample(I4cBaseModel):
    """Alarm condition for numeric values."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Data type.")
    aggregate_period: Optional[float] = Field(None, title="Aggregation period, seconds.")
    aggregate_count: Optional[int] = Field(None, title="Aggregation, number of samples.")
    aggregate_method: Optional[AlarmCondSampleAggMethod] = Field(AlarmCondSampleAggMethod.avg,
                                                                 title="Aggregation function.")
    rel: Optional[AlarmCondSampleRel] = Field(AlarmCondSampleRel.eq, title="Relation.")
    value: float = Field(..., title="Value.")

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
                            self.aggregate_method, self.rel.nice_value(), self.value)


    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('aggregate_period') is not None else 0
        x += 1 if values.get('aggregate_count') is not None else 0
        if x > 1:
            raise I4cInputValidationError('aggregate_period and aggregate_count are exclusive')
        if x == 0:
            raise I4cInputValidationError('aggregate_period or aggregate_count are required')
        return values



class AlarmCondEvent(I4cBaseModel):
    """Alarm condition for events."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Data type.")
    rel: Optional[CondEventRel] = Field(CondEventRel.eq, title="Relation")
    value: str = Field(..., title="Value.")
    age_min: Optional[float] = Field(None, title="Value persists for minimum, seconds.")
    age_max: Optional[float] = Field(None, title="Value persists for maximum, seconds.")

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
                            self.data_id, self.rel.nice_value(), self.value,
                            self.age_min, self.age_max)


class AlarmCondConditionValue(str, Enum):
    normal = "Normal"
    abnormal = "Abnormal"
    fault = "Fault"
    warning = "Warning"


class AlarmCondCondition(I4cBaseModel):
    """Alarm condition for condition types."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Condition type.")
    value: AlarmCondConditionValue = Field(..., title="Value.")
    age_min: Optional[float] = Field(None, title="Active at least since, seconds")

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
    """Alarm condition without id. Only one field should be non-null."""
    sample: Optional[AlarmCondSample] = Field(None, title="Numeric data condition")
    event: Optional[AlarmCondEvent] = Field(None, title="Event type condition")
    condition: Optional[AlarmCondCondition] = Field(None, title="Condition typed condition.")

    @root_validator
    def check_exclusive(cls, values):
        nones = tuple(values.get(s) for s in ('sample', 'event', 'condition')).count(None)
        if nones < 2:
            raise I4cInputValidationError('Sample, event, and condition are exclusive.')
        if nones == 3:
            raise I4cInputValidationError('Sample, event, or condition is required.')
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
    """Alarm condition. Only one field should be non-null."""
    id: int


class AlarmDefIn(I4cBaseModel):
    """Alarm definition. Input."""
    conditions: List[AlarmCond]
    max_freq: Optional[float] = Field(None, title="Max checking frequency, seconds.")
    window: Optional[float] = Field(None, title="Observation window, seconds.", description="Observation window in seconds. Useful when there is no event or condition filtering.")
    subsgroup: str = Field(..., title="Subscription group to be notified.")
    status: Optional[CommonStatusEnum] = Field(CommonStatusEnum.active, title="Status.")


class AlarmMethod(str, Enum):
    """Notification method."""
    email = "email"
    push = "push"
    none = "none"
    telegram = "telegram"


class AlarmSubIn(I4cBaseModel):
    """Subscriber to an alarm. Input."""
    groups: List[str] = Field(..., title="Subscription group membership.")
    user: str = Field(..., title="User id.")
    method: AlarmMethod = Field(..., title="Notification method.")
    address: Optional[str] = Field(None, title="Address")
    address_name: Optional[str] = Field(None, title="Address description.")
    status: Optional[CommonStatusEnum] = Field(CommonStatusEnum.active, title="Status.")


class AlarmSub(AlarmSubIn):
    """Subscriber to an alarm."""
    id: int = Field(..., title="Identifier.")
    user_name: Optional[str] = Field(None, title="User name.")


class AlarmDef(AlarmDefIn):
    """Alarm definition."""
    id: int = Field(..., title="Identifier.")
    name: str = Field(..., title="Identifier name.")
    last_check: datetime = Field(..., title="Last check time.")
    last_report: Optional[datetime] = Field(None, title="Last report time.")
    subs: List[AlarmSub] = Field(..., title="Subscribers.")


class AlarmSubPatchCondition(I4cBaseModel):
    """Alarm subscription update, preliminary check. Updates will only be carried out if all checks pass."""
    flipped: Optional[bool] = Field(None, title="Pass if the condition does not hold.")
    status: Optional[CommonStatusEnum] = Field(None, title="Status matches.")
    address: Optional[str] = Field(None, title="Address matches.")
    address_name: Optional[str] = Field(None, title="Address name matches.")
    empty_address: Optional[bool] = Field(None, title="Address is empty.")
    empty_address_name: Optional[bool] = Field(None, title="Address name is empty.")
    has_group: Optional[str] = Field(None, title="Assigned to the group.")

    def match(self, alarmsub:AlarmSub):
        r = (((self.status is None) or (alarmsub.status == self.status))
             and ((self.address is None) or (self.address == alarmsub.address))
             and ((self.address_name is None) or (self.address_name == alarmsub.address_name))
             and ((self.empty_address is None) or (bool(alarmsub.address) != self.empty_address))
             and ((self.empty_address_name is None) or (bool(alarmsub.address_name) != self.empty_address_name))
             and ((self.has_group is None) or (self.has_group in alarmsub.groups))
             )

        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class AlarmSubPatchChange(I4cBaseModel):
    """
    Describes the changes to be done to a subscription. Part of an alarm subscription update. All null fields will be
    ignored.
    """
    status: Optional[CommonStatusEnum] = Field(None, title="Set status.")
    address: Optional[str] = Field(None, title="Set address.")
    clear_address: Optional[bool] = Field(None, title="If true, clear address.")
    address_name: Optional[str] = Field(None, title="Set address name.")
    clear_address_name: Optional[bool] = Field(None, title="If true, clear address name.")
    add_groups: Optional[List[str]] = Field(None, title="Add to the given groups.")
    set_groups: Optional[List[str]] = Field(None, title="Add to these groups, remove from all others.")
    remove_groups: Optional[List[str]] = Field(None, title="Remove from the given groups.")

    def is_empty(self):
        return self.status is None \
               and self.address is None \
               and self.address_name is None \
               and (self.clear_address is None or not self.clear_address) \
               and (self.clear_address_name is None or not self.clear_address_name) \
               and self.add_groups is None \
               and self.set_groups is None \
               and self.remove_groups is None


    @root_validator
    def check_exclusive(cls, values):
        address, clear_address = values.get('address'), values.get('clear_address')
        if address is not None and clear_address:
            raise ValueError('address and clear_address are exclusive')
        address_name, clear_address_name = values.get('address_name'), values.get('clear_address_name')
        if address_name is not None and clear_address_name:
            raise ValueError('address_name and clear_address_name are exclusive')

        add_group, set_groups, remove_group = values.get('add_group'), values.get('set_groups'), values.get('remove_group')
        if add_group is not None and set_groups is not None:
            raise ValueError('add_group and set_groups are exclusive')
        if remove_group is not None and set_groups is not None:
            raise ValueError('remove_group and set_groups are exclusive')
        return values


class AlarmSubPatchBody(I4cBaseModel):
    """Used for alarm subscriber update. If all conditions are met, the changes will be carried out."""
    conditions: Optional[List[AlarmSubPatchCondition]] = Field([], title="List of conditions to check before the update.")
    change: AlarmSubPatchChange = Field(..., title="The changes to do.")


class SubsGroups(I4cBaseModel):
    """Subscription group with member users."""
    name: str
    users: Optional[List[str]] = Field([])


class SubsGroupsIn(I4cBaseModel):
    """Subscription group with member users. Without name."""
    users: List[str] = Field(...)


class SubsGroupsUser(I4cBaseModel):
    """Subscription groups belonging to a user."""
    user: str
    groups: Optional[List[str]] = Field([])


class AlarmEventCheckResult(I4cBaseModel):
    """Returned by alarm event check. Represents an alarm that was triggered."""
    alarm: str = Field(..., title="Triggered alarm")
    alarmevent_count: int = Field(..., title="Number of created events for the alarm.")


class AlarmRecipientStatus(str, Enum):
    outbox = "outbox"
    sent = "sent"
    failed = "failed"
    deleted = "deleted"


class AlarmEvent(I4cBaseModel):
    """Created when an alarm condition is detected."""
    id: int = Field(..., title="Identifier")
    alarm: str = Field(..., title="The triggered alarm")
    created: datetime = Field(..., title="The timestamp when the alarm condition was detected.")
    summary: str = Field(..., title="One line description of the event.")
    description: str = Field(..., title="Detailed description of the event.")


class AlarmRecipUser(I4cBaseModel):
    """Information on a recipient user."""
    id: str
    name: str
    status: CommonStatusEnum


class AlarmRecip(I4cBaseModel):
    """Recipient of an alarm event. Reflects to the subscribers of the alarm the time when it was triggered."""
    id: int = Field(..., title="Identifier")
    event: AlarmEvent = Field(..., title="Alarm event.")
    alarm: str = Field(..., title="Alarm definition identifier.")
    method: AlarmMethod = Field(..., title="Notification method.")
    status: AlarmRecipientStatus = Field(..., title="Notification status.")
    user: AlarmRecipUser = Field(..., title="Information on the recipient user.")
    address: Optional[str] = Field(None, title="Recipient's address.")
    address_name: Optional[str] = Field(None, title="Description of the recipient's address.")
    fail_count: int = Field(..., title="Number of failed sending attempts.")
    backoff_until: Optional[datetime] = Field(None, title="Retry wait until timestamp.")


class AlarmRecipPatchCondition(I4cBaseModel):
    """Condition in an update to an alarm recipient."""
    flipped: Optional[bool] = Field(None, title="Pass if the condition does not hold.")
    status: Optional[List[AlarmRecipientStatus]] = Field(None, title="Status is one of the listed.")
    fail_count: Optional[int] = Field(None, title="Number of failed sending attempts.")

    def match(self, recip:AlarmRecip):
        r = (((self.status is None) or (recip.status in self.status))
             and ((self.fail_count is None) or (recip.fail_count == self.fail_count))
             )
        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class AlarmRecipPatchChange(I4cBaseModel):
    """
    Describes the changes to be done to an alarm recipient. Part of an alarm recipient update. Null fields will be
    ignored.
    """
    status: Optional[AlarmRecipientStatus] = Field(None, title="New status.")
    fail_count: Optional[int] = Field(None, title="Number of failed sending attempts.")
    backoff_until: Optional[datetime] = Field(None, title="Postponed until timestamp")
    del_backoff_until: bool = Field(False, title="Clear postpone timestamp")

    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('backoff_until') is not None else 0
        x += 1 if values.get('del_backoff_until') else 0
        if x > 1:
            raise I4cInputValidationError('backoff_until and del_backoff_until are exclusive')
        return values

    def is_empty(self):
        return ( self.status is None
                 and self.fail_count is None
                 and self.backoff_until is None
                 and not self.del_backoff_until
                 )


class AlarmRecipPatchBody(I4cBaseModel):
    """Change to an alarm recipient. If all conditions are met, the change is carried out."""
    conditions: Optional[List[AlarmRecipPatchCondition]] = Field([], title="Conditions evaluated before the change.")
    change: AlarmRecipPatchChange = Field(..., title="Requested changes.")


async def alarmsub_list(credentials, id=None, group=None, group_mask=None, user=None,
                        user_name=None, user_name_mask=None, method=None, status=None, address=None,
                        address_mask=None, alarm:str = None, *, pconn=None) -> List[AlarmSub]:
    sql = dedent("""\
            with
                res as (
                    select
                      als.id,
                      als.groups,
                      als."user",
                      als.method,
                      als.address,
                      als.address_name,
                      als.status,
                      u."name" as user_name
                    from alarm_sub als
                    left join "user" u on u.id = als."user"
                    ),
                al as (
                    select "name", subsgroup
                    from alarm
                    )
            select * from res
            where True
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}\n"
        if group is not None:
            params.append(group)
            sql += f"and res.groups @> array[${len(params)}]::varchar[200][]\n"
        if group_mask is not None:
            sql += "and exists (select * from unnest(res.groups) where " + common.db_helpers.filter2sql(group_mask, "unnest", params) + ")"
        if user is not None:
            params.append(user)
            sql += f"and res.user = ${len(params)}\n"
        if "any user" not in credentials.info_features:
            params.append(credentials.user_id)
            sql += f"and res.user = ${len(params)}\n"
        if user_name is not None:
            params.append(user_name)
            sql += f"and res.user_name = ${len(params)}\n"
        if user_name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(user_name_mask, "res.user_name", params)
        if method is not None:
            params.append(method)
            sql += f"and res.method = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if address is not None:
            params.append(address)
            sql += f"and res.address = ${len(params)}\n"
        if address_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(address_mask, "res.address", params)
        if alarm is not None:
            params.append(alarm)
            sql += f" and exists(select * from al where array[al.subsgroup] <@ res.groups and al.\"name\" = ${len(params)})"
        write_debug_sql("alarmsub_list.sql", sql, *params)
        res = await conn.fetch(sql, *params)
        return [AlarmSub(**dict(r)) for r in res]


async def alarmdef_get(credentials, name, *, pconn=None) -> Optional[AlarmDef]:
    async with DatabaseConnection(pconn) as conn:
        sql_alarm = dedent("""\
                           select
                             "id", "name", max_freq, last_check, last_report, "subsgroup", "window", "status"
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
                                                                rel=AlarmCondSampleRel.from_nice_value(r["rel"]),
                                                                value=r["value_num"],
                                                                age_min=r["age_min"],
                                                                age_max=r["age_max"])))
            if r["log_row_category"] == AlarmCondLogRowCategory.event:
                conds.append(AlarmCondId(id=r["id"],
                                         event=AlarmCondEvent(device=r["device"],
                                                              data_id=r["data_id"],
                                                              rel=CondEventRel.from_nice_value(r["rel"]),
                                                              value=r["value_text"],
                                                              age_min=r["age_min"],
                                                              age_max=r["age_max"])))
            if r["log_row_category"] == AlarmCondLogRowCategory.condition:
                conds.append(AlarmCondId(id=r["id"],
                                         condition=AlarmCondCondition(device=r["device"],
                                                                      data_id=r["data_id"],
                                                                      value=r["value_text"],
                                                                      age_min=r["age_min"])))

        subs = await alarmsub_list(credentials, group=idr["subsgroup"], pconn=conn)
        return AlarmDef(id=idr["id"],
                        name=idr["name"],
                        conditions=conds,
                        max_freq=idr["max_freq"],
                        window=idr["window"],
                        last_check=idr["last_check"],
                        last_report=idr["last_report"],
                        subsgroup=idr["subsgroup"],
                        subs=subs,
                        status=idr["status"]
                        )


async def alarmdef_put(credentials, name, alarm: AlarmDefIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            old_alarm = await alarmdef_get(credentials, name, pconn=conn)
            new_last_check = datetime.now()
            if old_alarm is None:
                sql_insert = dedent("""\
                    insert into alarm (name, max_freq, last_check, subsgroup, "window", "status") values ($1, $2, $3, $4, $5, $6)
                    returning id
                    """)
                alarm_id = (await conn.fetchrow(sql_insert, name, alarm.max_freq, new_last_check,
                                                alarm.subsgroup, alarm.window, alarm.status))[0]
                old_alarm = AlarmDef(
                        id=alarm_id,
                        name=name,
                        conditions=[],
                        max_freq=alarm.max_freq,
                        window=alarm.window,
                        last_check=new_last_check,
                        last_report=None,
                        subsgroup=alarm.subsgroup,
                        subs=await alarmsub_list(credentials, group=alarm.subsgroup, pconn=conn),
                        status=alarm.status
                        )
            else:
                sql_update = dedent("""\
                    update alarm set max_freq = $2, last_check = $3, subsgroup = $4, "window" = $5, "status" = $6 
                    where name = $1""")
                await conn.execute(sql_update, name, alarm.max_freq, new_last_check,
                                   alarm.subsgroup, alarm.window, alarm.status)
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


async def alarmdef_list(credentials, name_mask, status, report_after,
                        subs_status, subs_method, subs_address, subs_address_mask, subs_user, subs_user_mask,
                        *, pconn=None):
    sql = dedent("""\
            with
              s as (
                select als.*, u."name" as user_name
                from alarm_sub als
                left join "user" u on u.id = als."user")
            select name
            from "alarm" res
            where True
            """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(name_mask, "res.name", params)
        if status is not None:
            params.append(status)
            sql += f"and res.status = ${len(params)}\n"
        if report_after is not None:
            params.append(report_after)
            sql += f"and res.last_report >= ${len(params)}\n"
        if any(x is not None for x in (subs_status, subs_method, subs_address, subs_address_mask, subs_user, subs_user_mask)):
            sql_subs = f"and exists(select * from s where array[res.subsgroup] <@ s.groups"
            if subs_status is not None:
                params.append(subs_status)
                sql += f"and s.status = ${len(params)}\n"
            if subs_method is not None:
                params.append(subs_method)
                sql += f"and s.method = ${len(params)}\n"
            if subs_user is not None:
                params.append(subs_user)
                sql += f"and s.user_name = ${len(params)}\n"
            if subs_user_mask is not None:
                sql += "and " + common.db_helpers.filter2sql(subs_user_mask, "s.user_name", params)
            if subs_address is not None:
                params.append(subs_address)
                sql += f"and s.address = ${len(params)}\n"
            if subs_address_mask is not None:
                sql += "and " + common.db_helpers.filter2sql(subs_address_mask, "s.address", params)
            sql_subs += ")"
            sql += sql_subs
        alarms = await conn.fetch(sql, *params)

        res = []
        for r in alarms:
            d = await alarmdef_get(credentials, r[0], pconn=conn)
            res.append(d)
        return res


async def subsgroupsusage_list(credentials, user, *, pconn=None):
    sql = dedent("""\
            select "user", array_agg("group") as groups
            from alarm_subsgroup_map
            where
              ("user" = $1 or $1 is null)
              and ("user" = $2 or $2 is null)
            group by "user"
            """)
    async with DatabaseConnection(pconn) as conn:
        self_filter = None
        if "any user" not in credentials.info_features:
            self_filter = credentials.user_id

        res = await conn.fetch(sql, user, self_filter)
        res = [{"user":r["user"], "groups":r["groups"]} for r in res]
        return res


async def subsgroup_members(credentials, user=None, group=None, *, pconn=None):
    sql = dedent("""\
            with
              p as (select
                      $1::varchar(200) -- */ '1'::varchar(200)
                          as user,
                      $2::varchar(200) -- */ 'grpxxx'::varchar(200)
                          as group
                   ),
              gm as (
                  select g."group", array_agg(g."user") as "users"
                  from alarm_subsgroup_map g
                  cross join p
                  where p.user is null or p.user = g.user
                  group by g."group"
              )
            select
              g."group" as "name",
              coalesce(gm."users", array[]::varchar[]) "users"
            from alarm_subsgroup g
            cross join p
            left join gm on gm.group = g.group
            where p.group is null or p.group = g.group
            """)
    async with DatabaseConnection(pconn) as conn:
        return await conn.fetch(sql, user, group)


async def subsgroup_members_put(credentials, name, sub_groups_in: SubsGroupsIn, *, pconn=None):
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            found = await subsgroup_members(credentials, group=name, pconn=conn)
            if found:
                found_user = set(found[0]["users"])
            else:
                found_user = set()
                sql_insert = """insert into alarm_subsgroup ("group") values ($1)"""
                await conn.execute(sql_insert, name)
            needed_user = set(sub_groups_in.users)
            for i in needed_user - found_user:
                sql_insert_member = """insert into alarm_subsgroup_map ("user", "group") values ($1, $2)"""
                await conn.execute(sql_insert_member, i, name)
            for d in found_user - needed_user:
                sql_delete_member = """delete from alarm_subsgroup_map where "user" = $1 and "group" = $2"""
                await conn.execute(sql_delete_member, d, name)
    return SubsGroups(name=name, users=sub_groups_in.users)


async def subsgroup_delete(credentials, name, forced, *, pconn=None):
    # IF SET FOR AN ALARM, ALWAYS RETURN ERROR, even if forced=true
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql_check = """select *  from alarm where subsgroup = $1"""
            db_check = await conn.fetch(sql_check, name)
            if db_check:
                raise I4cClientError("Group already in use.")

            found = await subsgroup_members(credentials, group=name, pconn=conn)
            if not found:
                return
            found_user = found[0]["users"]
            if found_user:
                if forced:
                    await subsgroup_members_put(credentials, name, SubsGroupsIn(users=[]), pconn=conn)
                else:
                    raise I4cClientError("Group already in use.")
            sql_delete = """delete from alarm_subsgroup where "group" = $1"""
            await conn.execute(sql_delete, name)


async def post_alarmsub(credentials, alarmsub:AlarmSubIn) -> AlarmSub:
    if (credentials.user_id != alarmsub.user) and ("any user" not in credentials.info_features):
        raise I4cClientError("Unauthorized to access other users' subscriptions.")

    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql_mod = "insert into alarm_sub (groups, \"user\", method, address, address_name, status)\n" \
                      "values ($1, $2, $3, $4, $5, $6)" \
                      "returning id"
            id = (await conn.fetchrow(sql_mod,
                                      alarmsub.groups, alarmsub.user, alarmsub.method,
                                      alarmsub.address, alarmsub.address_name, alarmsub.status))[0]
            res = await alarmsub_list(credentials, id=id, pconn=conn)
            return res[0]


async def patch_alarmsub(credentials, id, patch: AlarmSubPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            al = await alarmsub_list(credentials, id=id, pconn=conn)
            if len(al) == 0:
                raise I4cClientNotFound("No record found")
            al = al[0]

            if (credentials.user_id != al.user) and ("any user" not in credentials.info_features):
                raise I4cClientError("Unauthorized to access other users' subscriptions.")

            match = True
            for cond in patch.conditions:
                match = cond.match(al)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)

            params = [id]
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
            if patch.change.address_name is not None:
                params.append(patch.change.address_name)
                sql += f"{sep}\"address_name\"=${len(params)}"
                sep = ",\n"
            if patch.change.clear_address:
                sql += f"{sep}\"address\"= null"
                sep = ",\n"
            if patch.change.clear_address_name:
                sql += f"{sep}\"address_name\"= null"
                sep = ",\n"
            if any(x is not None for x in (patch.change.add_groups, patch.change.set_groups, patch.change.remove_groups)):
                groups = set(al.groups)
                if patch.change.add_groups is not None:
                    groups.update(patch.change.add_groups)
                if patch.change.set_groups is not None:
                    groups = set(patch.change.set_groups)
                if patch.change.remove_groups is not None:
                    for ci in patch.change.remove_groups:
                        groups.discard(ci)
                groups = sorted(list(groups))
                params.append(groups)
                sql += f"{sep}\"groups\"=${len(params)}"
                sep = ",\n"
            sql += "\nwhere id = $1::int"
            await conn.execute(sql, *params)

            return PatchResponse(changed=True)


def calc_aggregate(method, agg_values, slope_kind: AlarmCondSampleAggSlopeKind):
    agg_values = [v for v in agg_values if v["value_num"] is not None]
    if not agg_values:
        return None
    if method == AlarmCondSampleAggMethod.avg:
        return sum(v["value_num"] for v in agg_values) / len(agg_values)
    elif method in (AlarmCondSampleAggMethod.median, AlarmCondSampleAggMethod.q1st, AlarmCondSampleAggMethod.q4th):
        o = sorted(v["value_num"] for v in agg_values)
        if method == AlarmCondSampleAggMethod.median:
            return frac_index(o, (len(o) - 1) / 2)
        elif method == AlarmCondSampleAggMethod.q1st:
            return frac_index(o, (len(o) - 1) / 5)
        elif method == AlarmCondSampleAggMethod.q3th:
            return frac_index(o, (len(o) - 1) * 4 / 5)
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


async def check_alarmevent(credentials, alarm: str, max_count, *, override_last_check=None, override_now=None):
    res = []
    param_now = datetime.now() if override_now is None else override_now
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql_alarm = dedent(f"""\
                select * from alarm
                where
                  status = '{CommonStatusEnum.active}' 
                  ( max_freq is null 
                    or last_report is null 
                    or ($1 > last_report + max_freq * interval '1 second'))""")
            params = [param_now]
            if alarm is not None:
                params.append(alarm)
                sql_alarm += f"and \"name\" = ${len(params)}\n"
            if max_count is not None:
                params.append(override_last_check)
                sql_alarm += f"order by ($1 - coalesce(${len(params)}, last_check)) / nullif(max_freq,0) desc, last_check asc\n"
            write_debug_sql("alarm.sql", sql_alarm, *params)
            db_alarm = await conn.fetch(sql_alarm, *params)
            for row_alarm_recno, row_alarm in enumerate(db_alarm, start=1):
                if max_count is not None and row_alarm_recno > max_count:
                    break

                last_check = row_alarm["last_check"] if override_last_check is None else override_last_check

                sql_cond = "select * from alarm_cond where alarm = $1 order by log_row_category" # cond/ev/sample order
                db_conds = await conn.fetch(sql_cond, row_alarm["id"])
                total_series = None
                if row_alarm["window"] is not None:
                    total_series = series_intersect.Series()
                    total_series.add(series_intersect.TimePeriod(last_check - timedelta(seconds=row_alarm["window"]), None))
                # todo 5: maybe use "timestamp" AND "sequence" for intervals instead of "timestamp" only
                for row_cond_recno, row_cond in enumerate(db_conds, start=1):
                    last_check_mod = last_check
                    if total_series is not None and row_cond["log_row_category"] == AlarmCondLogRowCategory.sample:
                        last_check_mod = min((i for i in (last_check_mod, total_series[0].start) if i is not None), default=None)
                    write_debug_sql(f"alarm_check_load_series_{row_alarm_recno}_{row_cond_recno}.sql",
                                    series_check_load_sql, row_cond["device"], row_cond["data_id"], last_check_mod, param_now)
                    db_series = await conn.fetch(series_check_load_sql, row_cond["device"], row_cond["data_id"], last_check_mod, param_now)
                    current_series = series_intersect.Series()
                    agg_values = []
                    for r_series_prev, r_series in prev_iterator(db_series, include_first=False):
                        if row_cond["log_row_category"] == AlarmCondLogRowCategory.condition:
                            if ( row_cond["value_text"] == r_series_prev["value_text"]
                               or (row_cond["value_text"] == AlarmCondConditionValue.abnormal
                                   and r_series_prev["value_text"] in (AlarmCondConditionValue.warning, AlarmCondConditionValue.fault)
                                   )
                                 ):
                                age_min = timedelta(seconds=row_cond["age_min"] if row_cond["age_min"] else 0)
                                if r_series_prev["timestamp"] + age_min < r_series["timestamp"]:
                                    t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min, r_series["timestamp"],
                                                                    f'{row_cond["device"]} {row_cond["data_id"]} {row_cond["value_text"]}'
                                                                    )
                                    current_series.add(t)
                        elif row_cond["log_row_category"] == AlarmCondLogRowCategory.event:
                            if check_rel(row_cond["rel"], row_cond["value_text"], r_series_prev["value_text"]):
                                age_min = timedelta(seconds=row_cond["age_min"] if row_cond["age_min"] and row_cond["age_min"] > 0 else 0)
                                age_max = timedelta(seconds=row_cond["age_max"]) if row_cond["age_max"] else None
                                if r_series_prev["timestamp"] + age_min < r_series["timestamp"]:
                                    if age_max is None or r_series["timestamp"] + age_max > r_series["timestamp"]:
                                        t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min,
                                                                        r_series["timestamp"],
                                                                        f'{row_cond["device"]} {row_cond["data_id"]} '
                                                                        f'{r_series_prev["value_text"]}       ({row_cond["rel"]} {row_cond["value_text"]})')
                                    else:
                                        t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min,
                                                                        r_series_prev["timestamp"] + age_max,
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
                                agg_values.append(r_series_prev)
                                while len(agg_values) > 0 \
                                        and (r_series["timestamp"] - agg_values[0]["timestamp"]).total_seconds() > row_cond["aggregate_period"]:
                                    del agg_values[0]
                            if row_cond["aggregate_count"]:
                                if len(agg_values) == row_cond["aggregate_count"]:
                                    aggregated_value = calc_aggregate(row_cond["aggregate_method"], agg_values, AlarmCondSampleAggSlopeKind.position)
                                    del agg_values[0]
                                agg_values.append(r_series_prev)

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
                    description = "\n\n".join(f'{s.start} - {s.end}\n{textwrap.indent(s.extra, " - ") if s is not None else ""}' for s in total_series)
                    alarm_event_id = (await conn.fetchrow(sql_insert, row_alarm["id"], summary, description))[0]

                    subs = await conn.fetch("select distinct \"user\", method, address, address_name "
                                            "from alarm_sub where groups @> ARRAY[$1]::varchar[200][] "
                                            "and \"status\" = 'active'", row_alarm["subsgroup"])
                    for sub in subs:
                        sql_r = dedent("""\
                                   insert into alarm_recipient (event, "user", method, address, address_name, "status")
                                   values ($1, $2, $3, $4, $5, $6)""")
                        await conn.execute(sql_r, alarm_event_id, sub["user"], sub["method"],
                                           sub["address"], sub["address_name"], AlarmRecipientStatus.outbox)
                    sql_update_alarm += ", last_report = $2"
                sql_update_alarm += "where id = $1"
                await conn.execute(sql_update_alarm, row_alarm["id"], param_now)

    return res


async def alarmevent_list(credentials, id=None, alarm=None, alarm_mask=None,
                          user=None, user_name=None, user_name_mask=None, before=None, after=None, *, pconn=None) -> List[AlarmEvent]:
    sql = dedent("""\
            with
                res as (
                    select
                      ae.id,
                      al."name" as alarm,
                      ae.created,
                      ae.summary,
                      ae.description
                    from alarm_event ae
                    left join "alarm" al on al.id = ae."alarm"
                    ),
                rec as (
                    select
                      ar.event,
                      ar."user",
                      u."name" as "user_name"
                    from alarm_recipient ar
                    left join "user" u on u.id = ar."user"
                )
            select * from res
            where True
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}\n"
        if alarm is not None:
            params.append(alarm)
            sql += f"and res.alarm = ${len(params)}\n"
        if alarm_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(alarm_mask, "res.alarm", params)
        if user is not None:
            params.append(user)
            sql += f"and exists (select * from rec where rec.event = res.id and rec.\"user\" = ${len(params)} )\n"
        if user_name is not None:
            params.append(user_name)
            sql += f"and exists (select * from rec where rec.event = res.id and rec.user_name = ${len(params)} )\n"
        if user_name_mask is not None:
            sql += "and exists (select * from rec where rec.event = res.id and " + common.db_helpers.filter2sql(user_name_mask, "rec.user_name", params) + ")"
        if before is not None:
            params.append(before)
            sql += f"and res.created <= ${len(params)}\n"
        if after is not None:
            params.append(after)
            sql += f"and res.created >= ${len(params)}\n"
        write_debug_sql("alarmevent_list.sql", sql, *params)
        res = await conn.fetch(sql, *params)
        return [AlarmEvent(**dict(r)) for r in res]


async def alarmrecips_list(credentials, id=None, alarm=None, alarm_mask=None, event=None,
                           user=None, user_name=None, user_name_mask=None, user_status=None,
                           method=None, status=None, no_backoff=None, *, pconn=None) -> List[AlarmRecip]:
    sql = dedent("""\
            with
                res as (
                    select
                      r.id,
                      a.name as alarm,
                      r.method,
                      r."status",
                      e.id as event_id,
                      e.created as event_created,
                      e.summary as event_summary,
                      e.description as event_description,
                      r."address",
                      r."address_name",
                      r."user",
                      u.name as user_name,
                      u."status" as user_status,
                      r.fail_count,
                      r.backoff_until
                    from alarm_recipient r
                    join alarm_event e on e.id = r.event
                    join alarm a on a.id = e.alarm
                    left join "user" u on u.id = r."user"
                )
            select * from res
            where True
          """)
    async with DatabaseConnection(pconn) as conn:
        params = []
        if id is not None:
            params.append(id)
            sql += f"and res.id = ${len(params)}\n"
        if alarm is not None:
            params.append(alarm)
            sql += f"and res.alarm = ${len(params)}\n"
        if alarm_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(alarm_mask, "res.alarm", params)
        if event is not None:
            params.append(event)
            sql += f"and res.event_id = ${len(params)}\n"
        if user is not None:
            params.append(user)
            sql += f"and res.\"user\" = ${len(params)}\n"
        if user_name is not None:
            params.append(user_name)
            sql += f"and res.user_name = ${len(params)}\n"
        if user_name_mask is not None:
            sql += "and " + common.db_helpers.filter2sql(user_name_mask, "res.user_name", params)
        if method is not None:
            params.append(method)
            sql += f"and res.method = ${len(params)}\n"
        if status is not None:
            params.append(status)
            sql += f"and res.\"status\" = ${len(params)}\n"
        if user_status is not None:
            params.append(user_status)
            sql += f"and res.\"user_status\" = ${len(params)}\n"
        if no_backoff:
            sql += f"and (res.backoff_until is null or res.backoff_until <= now()) \n"
        res = await conn.fetch(sql, *params)
        return [AlarmRecip(id=r["id"],
                           event=AlarmEvent(id=r["event_id"],
                                            alarm=r["alarm"],
                                            created=r["event_created"],
                                            summary=r["event_summary"],
                                            description=r["event_description"]),
                           alarm=r["alarm"],
                           method=r["method"],
                           status=r["status"],
                           address=r["address"],
                           address_name=r["address_name"],
                           user=AlarmRecipUser(id=r["user"],
                                               name=r["user_name"],
                                               status=r["user_status"]),
                           fail_count=r["fail_count"],
                           backoff_until=r["backoff_until"]
                           ) for r in res]


async def patch_alarmrecips(credentials, id, patch: AlarmRecipPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            recip = await alarmrecips_list(credentials, id=id, pconn=conn)
            if len(recip) == 0:
                raise I4cClientNotFound("No record found")
            recip = recip[0]

            match = True
            for cond in patch.conditions:
                match = cond.match(recip)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)

            params = [id]
            sql = "update alarm_recipient\nset\n"
            sep = ""
            if patch.change.status:
                params.append(patch.change.status)
                sql += f"{sep}\"status\"=${len(params)}"
                sep = ",\n"
            if patch.change.fail_count is not None:
                params.append(patch.change.fail_count)
                sql += f"{sep}\"fail_count\"=${len(params)}"
                sep = ",\n"
            if patch.change.backoff_until is not None:
                params.append(patch.change.backoff_until)
                sql += f"{sep}\"backoff_until\"=${len(params)}"
                sep = ",\n"
            if patch.change.del_backoff_until:
                sql += f"{sep}\"backoff_until\" = null"
                sep = ",\n"

            sql += "\nwhere id = $1::int"
            await conn.execute(sql, *params)

            return PatchResponse(changed=True)
