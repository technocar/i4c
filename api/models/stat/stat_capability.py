# -*- coding: utf-8 -*-
from enum import Enum

import isodate
from isodate import ISO8601Error
from datetime import datetime
from textwrap import dedent
from typing import Optional, List
from pydantic import root_validator, validator, Field
from common import series_intersect
from common.exceptions import I4cServerError
from common import I4cBaseModel
from common.cmp_list import cmp_list
from models import CondEventRel, alarm
from models.alarm import prev_iterator
from .stat_common import StatVisualSettings, resolve_time_period


class StatCapabilityFilter(I4cBaseModel):
    """Time series query, filter for Event data types."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Event type.")
    rel: CondEventRel = Field(..., title="Relation.")
    value: str = Field(..., title="Value.")

    @classmethod
    async def load_filters(cls, conn, capability):
        sql = "select * from stat_capability_filter where capability = $1"
        res = await conn.fetch(sql, capability)
        return [StatCapabilityFilter(**r) for r in res]

    async def insert_to_db(self, ts_id, conn):
        sql_insert = dedent("""\
            insert into stat_capability_filter (capability,
                                                device,data_id,rel,
                                                value
                                   ) values ($1,
                                             $2, $3, $4,
                                             $5)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, ts_id,
                                       self.device, self.data_id, self.rel,
                                       self.value))[0]

    def __eq__(self, other):
        if not isinstance(other, StatCapabilityFilter):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.rel == other.rel)
                and (self.value == other.value))


class StatCapabilityMetric(I4cBaseModel):
    """Time series query, the shown metric (Sample data type)."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Numeric data type.")


class StatCapabilityVisualSettingsInfoBoxLoc(str, Enum):
    none = "none"
    left = "left"
    right = "right"
    bottom = "bottom"
    top = "top"


class StatCapabilityVisualSettings(I4cBaseModel):
    """Capability query, visual settings."""
    title: Optional[str] = Field(None, title="Title.")
    subtitle: Optional[str] = Field(None, title="Subtitle.")
    plotdata: Optional[bool] = Field(False, title="Plotdata")
    infoboxloc: Optional[StatCapabilityVisualSettingsInfoBoxLoc] = Field(StatCapabilityVisualSettingsInfoBoxLoc.none, title="Info box location")

    @classmethod
    async def load_settings(cls, conn, id):
        sql = f"""select * from stat_capability_visual_setting where id = $1"""
        res = await conn.fetchrow(sql, id)
        if res:
            res = StatCapabilityVisualSettings(**res)
        else:
            res = StatCapabilityVisualSettings()
        return res


    async def insert_or_update_db(self, id, conn):
        exists = await conn.fetchrow("select id from stat_capability_visual_setting where id = $1", id)
        if exists:
            sql = dedent("""\
                update stat_capability_visual_setting
                set
                  title = $2,
                  subtitle = $3,
                  plotdata = $4, 
                  infoboxloc = $5
                where id = $1
                """)
        else:
            sql = dedent("""\
                insert into stat_capability_visual_setting (id, title, subtitle,
                                                      plotdata, infoboxloc
                                                      ) values ($1, $2, $3,
                                                                $4, $5)
                """)
        await conn.execute(sql, id, self.title, self.subtitle,
                           self.plotdata, self.infoboxloc)


class StatCapabilityDef(I4cBaseModel):
    """
    Time series query definition. After and before are exclusive. If both omitted, before defaults to now.
    If before is set, duration is required. If after is set, default duration extends to now.
    """
    after: Optional[datetime] = Field(None, title="Query data after this time.")
    before: Optional[datetime] = Field(None, title="Query data before this time.")
    duration: Optional[str] = Field(None, title="Observed period length.")
    filter: List[StatCapabilityFilter] = Field(..., title="Event and Condition filters.")
    metric: StatCapabilityMetric = Field(..., title="The displayed metric, numeric data type.")
    nominal: float = Field(..., title="Nominal")
    utl: float = Field(..., title="Utl")
    ltl: float = Field(..., title="Ltl")
    ucl: Optional[float] = Field(None, title="Ucl")
    lcl: Optional[float] = Field(None, title="Lcl")
    visualsettings: StatCapabilityVisualSettings = Field(..., title="Chart settings.")

    @validator('duration')
    def duration_validator(cls, v):
        if v is not None:
            try:
                isodate.parse_duration(v)
            except ISO8601Error:
                raise ValueError('Invalid duration format. Use ISO8601')
        return v

    @root_validator
    def check_exclusive(cls, values):
        after_s, before_s, duration_s = values.get('after') is not None, values.get('before') is not None, values.get('duration') is not None
        period_s = sum(int(x) for x in (after_s, before_s, duration_s))
        if period_s in (0,3) or (period_s == 1 and before_s):
            raise ValueError('invalid (after, before, duration) configuration.')
        return values

    async def insert_to_db(self, stat_id, conn):
        sql_insert = dedent("""\
            insert into stat_capability (id,
                                         after, before, duration,
                                         metric_device, metric_data_id, nominal,
                                         utl, ltl, ucl,
                                         lcl)
            select $1,
                   $2, $3, $4::varchar(200)::interval,
                   $5, $6, $7,
                   $8, $9, $10,
                   $11
            """)
        await conn.execute(sql_insert, stat_id, *self.get_sql_params())

        for f in self.filter:
            await f.insert_to_db(stat_id, conn)

        await self.visualsettings.insert_or_update_db(stat_id, conn)

    def get_sql_params(self):
        return [self.after, self.before, self.duration,
                self.metric.device, self.metric.data_id, self.nominal,

                self.utl, self.ltl, self.ucl,
                self.lcl]


    async def update_to_db(self, stat_id, new_state, conn):
        """
        :param stat_id:
        :param new_state: StatCapabilityDef
        :param conn:
        :return:
        """
        sql_update = dedent("""\
            update stat_capability
            set
              after=$2,
              before=$3,
              duration=$4::varchar(200)::interval,

              metric_device=$5,
              metric_data_id=$6,
              nominal=$7,

              utl=$8,
              ltl=$9,
              ucl=$10,

              lcl=$11
            where id = $1
            """)
        await conn.execute(sql_update, stat_id, *new_state.get_sql_params())

        insert, delete, _, _ = cmp_list(self.filter, new_state.filter)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatCapabilityFilter")
            await conn.execute("delete from stat_capability_filter where id = $1", d.id)

        await new_state.visualsettings.insert_or_update_db(stat_id, conn)


    @classmethod
    def create_from_dict(cls, d, prefix, keep_prefix=None):
        if prefix:
            dn = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
            if keep_prefix:
                for p in keep_prefix:
                    dn.update({k: v for k, v in d.items() if k.startswith(p)})
        else:
            dn = dict(d)
        d = dn
        del dn

        if d["id"] is None:
            return None
        d["metric"] = StatCapabilityMetric(device=d["metric_device"], data_id=d["metric_data_id"])
        return StatCapabilityDef(**d)


class StatCapabilityData(I4cBaseModel):
    """
    Result for capability query.
    """
    points: Optional[List[float]] = Field(None, title="Values.")
    count: int = Field(None, title="Count.")
    min: Optional[float] = Field(None, title="Min.")
    max: Optional[float] = Field(None, title="Max.")
    mean: Optional[float] = Field(None, title="Mean.")
    sigma: Optional[float] = Field(None, title="Sigma.")
    c: Optional[float] = Field(None, title="C.")
    ck: Optional[float] = Field(None, title="Ck.")


async def statdata_get_capability(credentials, st_id:int, st_capabilitydef: StatCapabilityDef, conn) -> StatCapabilityData:
    after, before = resolve_time_period(st_capabilitydef.after, st_capabilitydef.before, st_capabilitydef.duration)

    total_series = series_intersect.Series()
    total_series.add(series_intersect.TimePeriod(after, before))

    filters = await conn.fetch("select * from stat_capability_filter where capability = $1", st_id)
    # todo 5: maybe use "timestamp" AND "sequence" for intervals instead of "timestamp" only
    for filter in filters:
        db_series = await conn.fetch(alarm.alarm_check_load_sql, filter["device"], filter["data_id"], after, before)
        current_series = series_intersect.Series()
        for r_series_prev, r_series in prev_iterator(db_series, include_first=False):
            if alarm.check_rel(filter["rel"], filter["value"], r_series_prev["value_text"]):
                t = series_intersect.TimePeriod(r_series_prev["timestamp"], r_series["timestamp"])
                current_series.add(t)
        total_series = series_intersect.Series.intersect(total_series, current_series)
        del current_series


    res = dict(points=[], mean=None, sigma=None, c=None, ck=None)
    if len(total_series) > 0:
        md_series = await conn.fetch(alarm.alarm_check_load_sql,
                                     st_capabilitydef.metric.device,
                                     st_capabilitydef.metric.data_id,
                                     total_series[0].start or after,
                                     total_series[-1].end or before)

        for md_prev, md in prev_iterator(md_series, include_first=False):
            if not total_series.is_timestamp_in(md_prev["timestamp"]):
                continue
            if md_prev["value_num"] is not None:
                res["points"].append(md_prev["value_num"])

        res["count"] = len(res["points"])
        if res["count"] > 0:
            res["min"] = min(res["points"])
            res["max"] = max(res["points"])
            res["mean"] = sum(res["points"]) / len(res["points"])
            res["sigma"] = (sum((i - res["mean"]) ** 2 for i in res["points"]) / (len(res["points"]) - 1)) ** (1 / 2) \
                if len(res["points"]) > 1 else 0
            res["c"] = (st_capabilitydef.utl - st_capabilitydef.ltl) / (3 * res["sigma"]) if res["sigma"] != 0 else None
            res["ck"] = min( (st_capabilitydef.utl - res["mean"]) / (1.5*res["sigma"]),
                             (res["mean"] - st_capabilitydef.ltl) / (1.5*res["sigma"]) ) if res["sigma"] != 0 else None

    return StatCapabilityData(**res)
