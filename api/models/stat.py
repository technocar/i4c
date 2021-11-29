from datetime import datetime, timedelta, timezone
from enum import Enum
from textwrap import dedent
from typing import Optional, List

from fastapi import HTTPException
from isodate import ISO8601Error
from pydantic import root_validator, validator, Field
import common.db_helpers
from common import I4cBaseModel, DatabaseConnection, CredentialsAndFeatures, series_intersect
import isodate

from common.cmp_list import cmp_list
from common.tools import frac_index, optimize_timestamp_label
from models import AlarmCondEventRel, alarm
from models.alarm import prev_iterator
from models.common import PatchResponse


class StatUser(I4cBaseModel):
    id: int
    name: str

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        if d["id"] is None:
            return None
        return StatUser(**d)



class StatTimeseriesFilter(I4cBaseModel):
    """ category="EVENT" only """
    id: Optional[int]
    device: str
    data_id: str
    rel: AlarmCondEventRel
    value: str
    age_min: Optional[float] = Field(None, description="sec")
    age_max: Optional[float] = Field(None, description="sec")

    @classmethod
    async def load_filters(cls, conn, timeseries):
        sql = "select * from stat_timeseries_filter where timeseries = $1"
        res = await conn.fetch(sql, timeseries)
        return [StatTimeseriesFilter(**r) for r in res]

    async def insert_to_db(self, ts_id, conn):
        sql_insert = dedent("""\
            insert into stat_timeseries_filter (timeseries,
                                                device,data_id,rel,
                                                value,age_min,age_max    
                                   ) values ($1, 
                                             $2, $3, $4, 
                                             $5, $6, $7)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, ts_id,
                                       self.device, self.data_id, self.rel,
                                       self.value, self.age_min, self.age_max))[0]

    def __eq__(self, other):
        if not isinstance(other, StatTimeseriesFilter):
            return False
        return ((self.device == other.device)
                and (self.data_id == other.data_id)
                and (self.rel == other.rel)
                and (self.value == other.value)
                and (self.age_min == other.age_min)
                and (self.age_max == other.age_max))


class StatTimeseriesMetric(I4cBaseModel):
    """ category="SAMPLE" only """
    device: str
    data_id: str


class StatTimeseriesAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1th"
    q3rd = "q3rd"
    min = "min"
    max = "max"


class StatTimeseriesSeriesName(str, Enum):
    separator_event = "separator_event"
    sequence = "sequence"
    timestamp = "timestamp"


class StatTimeseriesXAxis(str, Enum):
    timestamp = "timestamp"
    sequence = "sequence"


class StatTimeseriesType(str, Enum):
    timeseries = "timeseries"
    xy = "xy"


class StatSepEvent(I4cBaseModel):
    """ category="EVENT" only """
    device: str
    data_id: str

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        if all(x is not None for x in (d["device"], d["data_id"])):
            return StatSepEvent(device=d["device"], data_id=d["data_id"])
        return None


class StatTimeseriesVisualSettings(I4cBaseModel):
    # todo 1: **********
    pass


class StatTimeseriesDef(I4cBaseModel):
    after: Optional[datetime]
    before: Optional[datetime]
    duration: Optional[str]
    filter: List[StatTimeseriesFilter]
    metric: StatTimeseriesMetric
    agg_func: Optional[StatTimeseriesAggMethod]
    agg_sep: Optional[StatSepEvent]
    series_sep: Optional[StatSepEvent]
    series_name: Optional[StatTimeseriesSeriesName]
    xaxis: StatTimeseriesXAxis
    visualsettings: StatTimeseriesVisualSettings

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

        agg_func_s, agg_sep_s = values.get('agg_func') is not None, values.get('agg_sep') is not None
        if agg_func_s != agg_sep_s:
            raise ValueError('agg_func and agg_sep both must be present or ommited')
        return values

    async def insert_to_db(self, stat_id, conn):
        sql_insert = dedent("""\
            insert into stat_timeseries (id,
                                         after, before, duration,
                                         metric_device, metric_data_id, agg_func,
                                         agg_sep_device, agg_sep_data_id, series_name,
                                         series_sep_device, series_sep_data_id, xaxis)
            select $1, 
                   $2, $3, $4::varchar(200)::interval, 
                   $5, $6, $7, 
                   $8, $9, $10, 
                   $11, $12, $13
            """)
        await conn.execute(sql_insert, stat_id, *self.get_sql_params())

        for f in self.filter:
            await f.insert_to_db(stat_id, conn)

    def get_sql_params(self):
        return [self.after, self.before, self.duration,
                self.metric.device, self.metric.data_id, self.agg_func,

                self.agg_sep.device if self.agg_sep is not None else None,
                self.agg_sep.data_id if self.agg_sep is not None else None,
                self.series_name,

                self.series_sep.device if self.series_sep is not None else None,
                self.series_sep.data_id if self.series_sep is not None else None,
                self.xaxis]


    async def update_to_db(self, stat_id, new_state, conn):
        """
        :param stat_id:
        :param new_state: StatTimeseriesDef
        :param conn:
        :return:
        """
        sql_update = dedent("""\
            update stat_timeseries
            set
              after=$2,
              before=$3,
              duration=$4::varchar(200)::interval,
              
              metric_device=$5,
              metric_data_id=$6,
              agg_func=$7,
              
              agg_sep_device=$8,
              agg_sep_data_id=$9,
              series_name=$10,
              
              series_sep_device=$11,
              series_sep_data_id=$12,
              xaxis=$13
            where id = $1
            """)
        await conn.execute(sql_update, stat_id, *new_state.get_sql_params())

        insert, delete, _, _ = cmp_list(self.filter, new_state.filter)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise HTTPException(status_code=500, detail="Missing id from StatTimeseriesFilter")
            await conn.execute("delete from stat_timeseries_filter where id = $1", d.id)


    @classmethod
    def get_visualsettings(cls):
        # todo 1: **********
        return StatTimeseriesVisualSettings()

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        if d["id"] is None:
            return None
        d["metric"] = StatTimeseriesMetric(device=d["metric_device"], data_id=d["metric_data_id"])
        d["agg_sep"] = StatSepEvent.create_from_dict(d, "agg_sep_")
        d["series_sep"] = StatSepEvent.create_from_dict(d, "series_sep_")
        d["visualsettings"] = cls.get_visualsettings()
        return StatTimeseriesDef(**d)


class StatXYObject(str, Enum):
    workpiece = "workpiece"
    mazakprogram = "mazakprogram"
    batch = "batch"
    tool = "tool"


class StatXYFieldDef(I4cBaseModel):
    name: str
    # todo ?: params: List[str]


class StatXYVisualSettings(I4cBaseModel):
    # todo 1: **********
    pass


class StatXYFilterRel(str, Enum):
    eq = "="
    neq = "!="
    less = "<"
    leq = "<="
    gtr = ">"
    geq = ">="


class StatXYFilter(I4cBaseModel):
    field: StatXYFieldDef
    rel: StatXYFilterRel
    value: str


class StatXYDef(I4cBaseModel):
    objname: StatXYObject
    after: Optional[datetime]
    before: Optional[datetime]
    duration: Optional[str]
    x: StatXYFieldDef
    y: Optional[StatXYFieldDef]
    shape: StatXYFieldDef
    color: StatXYFieldDef
    others: List[StatXYFieldDef]
    filters: List[StatXYFilter]
    visualsettings: StatXYVisualSettings

    async def insert_to_db(self, stat_id, conn):
        # todo 1: **********
        pass


class StatDefIn(I4cBaseModel):
    name: str
    shared: bool
    timeseriesdef: Optional[StatTimeseriesDef]
    xydef: Optional[StatXYDef]

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef_s, xydef_s = values.get('timeseriesdef') is not None, values.get('xydef') is not None
        if sum(int(x) for x in (timeseriesdef_s, xydef_s)) != 1:
            raise ValueError('Exactly one of timeseriesdef or xydef should be present')
        return values


class StatDef(StatDefIn):
    id: int
    user: StatUser
    modified: datetime


class StatPatchCondition(I4cBaseModel):
    flipped: Optional[bool]
    shared: Optional[bool]

    def match(self, stat:StatDef):
        r = ((self.shared is None) or (stat.shared == self.shared))

        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class StatPatchChange(I4cBaseModel):
    shared: Optional[bool]
    timeseriesdef: Optional[StatTimeseriesDef]
    xydef: Optional[StatXYDef]

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef, xydef = values.get('timeseriesdef'), values.get('xydef')
        if timeseriesdef is not None and xydef is not None:
            raise ValueError('timeseriesdef and xydef are exclusive')
        return values

    def is_empty(self):
        return self.timeseriesdef is None and self.xydef is None


class StatPatchBody(I4cBaseModel):
    conditions: List[StatPatchCondition]
    change: StatPatchChange


async def stat_list(credentials, id=None, user_id=None, name=None, name_mask=None,
                    type:Optional[StatTimeseriesType] = None, *, pconn=None) -> List[StatDef]:
    sql = dedent("""\
            with 
                res as (
                    select 
                      s.id, s."name", s.shared, s.modified,
                      
                      u."id" as u_id, u."name" as u_name, 
                      
                      st.id as st_id, 
                      st.after as st_after,
                      st.before as st_before,
                      st.duration::varchar(200) as st_duration,
                      st.metric_device as st_metric_device,
                      st.metric_data_id as st_metric_data_id,
                      st.agg_func as st_agg_func,
                      st.agg_sep_device as st_agg_sep_device,
                      st.agg_sep_data_id as st_agg_sep_data_id,
                      st.series_name as st_series_name,
                      st.series_sep_device as st_series_sep_device,
                      st.series_sep_data_id as st_series_sep_data_id,
                      st.xaxis as st_xaxis  
                    from stat s
                    join "user" u on u.id = s."user"
                    left join "stat_timeseries" st on st."id" = s."id"
                    )                
            select * from res
            where True
          """)
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL intervalstyle = 'iso_8601';")
            params = []
            if id is not None:
                params.append(id)
                sql += f"and res.id = ${len(params)}\n"
            if user_id is not None:
                params.append(user_id)
                sql += f"and res.user = ${len(params)}\n"
            if name is not None:
                params.append(name)
                sql += f"and res.\"name\" = ${len(params)}\n"
            if name_mask is not None:
                sql += "and " + common.db_helpers.filter2sql(name_mask, "res.\"name\"", params)
            if type is not None:
                if type == StatTimeseriesType.timeseries:
                    sql += f"and res.st_id is not null\n"
            res_db = await conn.fetch(sql, *params)
            res = []
            for r in res_db:
                d = dict(r)
                d["user"] = StatUser.create_from_dict(d, 'u_')
                if d["st_id"] is not None:
                    d["st_filter"] = await StatTimeseriesFilter.load_filters(conn, d["st_id"])
                    timeseriesdef = StatTimeseriesDef.create_from_dict(d,'st_')
                # todo: xydef
                res.append(StatDef(**d,timeseriesdef=timeseriesdef))
            return res


async def stat_post(credentials:CredentialsAndFeatures, stat: StatDefIn) -> StatDef:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql = "select * from stat where name = $1 and \"user\" = $2"
            old_db = await conn.fetch(sql, stat.name, credentials.user_id)
            if old_db:
                raise HTTPException(status_code=400, detail="Name already in use")

            sql_insert = dedent("""\
                insert into stat (name, "user", shared, modified) values ($1, $2, $3, now())
                returning id
            """)
            stat_id = (await conn.fetchrow(sql_insert, stat.name, credentials.user_id, stat.shared))[0]
            sql_user_name = "select \"name\" from \"user\" where id = $1"
            user_display_name = (await conn.fetchrow(sql_user_name, credentials.user_id))[0]

            if stat.timeseriesdef is not None:
                await stat.timeseriesdef.insert_to_db(stat_id, conn)

            if stat.xydef is not None:
                await stat.xydef.insert_to_db(stat_id, conn)

            return StatDef(id=stat_id,
                           user=StatUser(id=credentials.user_id, name=user_display_name),
                           modified=datetime.now(timezone.utc),
                           name=stat.name,
                           shared=stat.shared,
                           timeseriesdef=stat.timeseriesdef,
                           xydef=stat.xydef)


async def stat_delete(credentials, id):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise HTTPException(status_code=404, detail="No record found")
            st = st[0]

            if st.user != credentials.user_id:
                if 'delete any' not in credentials.info_features:
                    raise HTTPException(status_code=400, detail="Unable to delete other's statistics")

            sql = "delete from stat where id = $1"
            await conn.execute(sql, id)


async def stat_patch(credentials, id, patch:StatPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise HTTPException(status_code=404, detail="No record found")
            st = st[0]

            if st.user != credentials.user_id:
                if 'patch any' not in credentials.info_features:
                    raise HTTPException(status_code=400, detail="Unable to modify other's statistics")

            match = True
            for cond in patch.conditions:
                match = cond.match(st)
                if not match:
                    break
            if not match:
                return PatchResponse(changed=False)

            if patch.change.is_empty():
                return PatchResponse(changed=True)

            params = [id]
            sql = "update stat\nset\nmodified=now()"
            if patch.change.shared is not None:
                params.append(patch.change.shared)
                sql += f",\nshared = ${len(params)}::boolean"
            sql += "\nwhere id = $1"
            await conn.execute(sql, *params)

            if patch.change.timeseriesdef is not None:
                if st.xydef is not None:
                    # todo: clear xydef
                    pass
                if st.timeseriesdef is not None:
                    await st.timeseriesdef.update_to_db(st.id, patch.change.timeseriesdef, conn)
                else:
                    await patch.change.timeseriesdef.insert_to_db(st.id, conn)

            if patch.change.xydef is not None:
                if st.timeseriesdef is not None:
                    conn.execute('delete from stat_timeseries where "id" = $1', st.id)
                # todo: update xydef

            return PatchResponse(changed=True)


class StatTimeseriesDataSeries(I4cBaseModel):
    name: str
    x_timestamp: Optional[List[datetime]]
    x_relative: Optional[List[float]] = Field(None, description="relative sec to first item")
    y: List[float]


class StatXYData(I4cBaseModel):
    # todo 1: **********
    pass


class StatData(I4cBaseModel):
    stat_def: StatDef
    timeseriesdata: Optional[List[StatTimeseriesDataSeries]]
    xydata: Optional[List[StatXYData]]


def resolve_time_period(after, before, duration):
    def v(*val):
        return all(x is not None for x in val)

    duration = isodate.parse_duration(duration) if v(duration) else None
    before = before if v(before) else after + duration if v(after, duration) else datetime.now(timezone.utc)
    after = after if v(after) else before - duration
    return after, before


def calc_aggregate(method: StatTimeseriesAggMethod, agg_values):
    agg_values = [v for v in agg_values if v["value_num"] is not None]
    if not agg_values:
        return None
    if method == StatTimeseriesAggMethod.avg:
        return sum(v["value_num"] for v in agg_values) / len(agg_values)
    elif method in (StatTimeseriesAggMethod.median, StatTimeseriesAggMethod.q1st, StatTimeseriesAggMethod.q4st):
        o = sorted(v["value_num"] for v in agg_values)
        if method == StatTimeseriesAggMethod.median:
            return frac_index(o, (len(o) - 1) / 2)
        elif method == StatTimeseriesAggMethod.q1st:
            return frac_index(o, (len(o) - 1) / 4)
        elif method == StatTimeseriesAggMethod.q3th:
            return frac_index(o, (len(o) - 1) * 3 / 4)
    elif method == StatTimeseriesAggMethod.min:
        return min(v["value_num"] for v in agg_values)
    elif method == StatTimeseriesAggMethod.max:
        return max(v["value_num"] for v in agg_values)


async def statdata_get_timeseries(st:StatDef, conn) -> StatData:
    after, before = resolve_time_period(st.timeseriesdef.after, st.timeseriesdef.before, st.timeseriesdef.duration)

    total_series = series_intersect.Series()
    total_series.add(series_intersect.TimePeriod(after, before))

    filters = await conn.fetch("select * from stat_timeseries_filter where timeseries = $1", st.id)
    # todo 5: maybe use "timestamp" AND "sequence" for intervals instead of "timestamp" only
    for filter in filters:
        db_series = await conn.fetch(alarm.alarm_check_load_sql, filter["device"], filter["data_id"], after, before)
        current_series = series_intersect.Series()
        for r_series_prev, r_series in prev_iterator(db_series, include_first=False):
            if alarm.check_rel(filter["rel"], filter["value"], r_series_prev["value_text"]):
                age_min = timedelta(seconds=filter["age_min"] if filter["age_min"] else 0)
                age_max = timedelta(seconds=filter["age_max"] if filter["age_max"] else 0)
                if r_series_prev["timestamp"] + age_min < r_series["timestamp"] - age_max:
                    t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min,
                                                    r_series["timestamp"] - age_max)
                    current_series.add(t)
        total_series = series_intersect.Series.intersect(total_series, current_series)
        del current_series


    def create_StatTimeseriesDataSeries():
        res = StatTimeseriesDataSeries(name="", y=[])
        if st.timeseriesdef.xaxis == StatTimeseriesXAxis.timestamp:
            res.x_relative = []
            res.x_timestamp = []
        return res

    current_series = create_StatTimeseriesDataSeries()
    res = StatData(stat_def=st, timeseriesdata=[current_series])
    last_series_sep_value = None

    def record_output(aggregated_value, ts):
        if aggregated_value is None:
            return
        if (current_series.name == "") and st.timeseriesdef.series_name:
            if st.timeseriesdef.series_name == StatTimeseriesSeriesName.separator_event:
                if last_series_sep_value:
                    current_series.name = last_series_sep_value
            elif st.timeseriesdef.series_name == StatTimeseriesSeriesName.sequence:
                current_series.name = str(len(res.timeseriesdata))
        if current_series.x_timestamp is not None:
            current_series.x_timestamp.append(ts)
            if current_series.x_relative is not None:
                current_series.x_relative.append((ts-current_series.x_timestamp[0]).total_seconds())
        current_series.y.append(aggregated_value)

    if len(total_series) > 0:
        md_series = await conn.fetch(alarm.alarm_check_load_sql,
                                     st.timeseriesdef.metric.device,
                                     st.timeseriesdef.metric.data_id,
                                     total_series[0].start or after,
                                     total_series[-1].end or before)
        agg_sep_ts = []
        if st.timeseriesdef.agg_sep:
            agg_sep_series = await conn.fetch(alarm.alarm_check_load_sql,
                                         st.timeseriesdef.agg_sep.device,
                                         st.timeseriesdef.agg_sep.data_id,
                                         total_series[0].start or after,
                                         total_series[-1].end or before)
            agg_sep_ts = [r["timestamp"] for r in agg_sep_series]

        series_sep_ts = []
        if st.timeseriesdef.series_sep:
            series_sep_series = await conn.fetch(alarm.alarm_check_load_sql,
                                         st.timeseriesdef.series_sep.device,
                                         st.timeseriesdef.series_sep.data_id,
                                         total_series[0].start or after,
                                         total_series[-1].end or before)
            series_sep_ts = [(r["timestamp"], r["value_text"]) for r in series_sep_series]

        agg_values = []
        md_prev = None
        for md_prev, md in prev_iterator(md_series, include_first=False):
            if not total_series.is_timestamp_in(md_prev["timestamp"]):
                continue

            aggregated_value = None
            if st.timeseriesdef.agg_sep:
                while agg_sep_ts and agg_sep_ts[0] < md_prev["timestamp"]:
                    del agg_sep_ts[0]
                if agg_sep_ts and agg_sep_ts[0] < md["timestamp"]:
                    aggregated_value = calc_aggregate(st.timeseriesdef.agg_func, agg_values)
                    agg_values = []
                agg_values.append(md_prev)
            else:
                aggregated_value = md_prev["value_num"]

            while series_sep_ts and series_sep_ts[0][0] < md_prev["timestamp"]:
                last_series_sep_value = series_sep_ts[0][1]
                del series_sep_ts[0]

            record_output(aggregated_value, md_prev["timestamp"])

            if series_sep_ts and series_sep_ts[0][0] < md["timestamp"]:
                current_series = create_StatTimeseriesDataSeries()
                res.timeseriesdata.append(current_series)

        if agg_values:
            aggregated_value = calc_aggregate(st.timeseriesdef.agg_func, agg_values)
            record_output(aggregated_value, md_prev["timestamp"])

    if st.timeseriesdef.series_name == StatTimeseriesSeriesName.timestamp:
        ts = [(s.x_timestamp[0],s) for s in res.timeseriesdata if s.x_timestamp]
        tso = optimize_timestamp_label([s[0] for s in ts])
        for s, o in zip(ts, tso):
            s[1].name = o
    return res


async def statdata_get_xy(st:StatDef, conn) -> StatData:
    # todo 1: **********
    pass


async def statdata_get(credentials, id) -> StatData:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise HTTPException(status_code=404, detail="No record found")
            st = st[0]
            if st.timeseriesdef is not None:
                return await statdata_get_timeseries(st, conn)
            elif st.xydef is not None:
                return await statdata_get_xy(st, conn)
            return StatData()
