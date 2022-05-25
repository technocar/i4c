# -*- coding: utf-8 -*-
import isodate
from isodate import ISO8601Error
from datetime import datetime, timedelta
from enum import Enum
from textwrap import dedent
from typing import Optional, List
from pydantic import root_validator, validator, Field
from common import series_intersect
from common.exceptions import I4cServerError
from common import I4cBaseModel
from common.cmp_list import cmp_list
from common.tools import optimize_timestamp_label
from models import CondEventRel, alarm
from models.alarm import prev_iterator
from .stat_common import StatAggMethod, StatVisualSettings, resolve_time_period, calc_aggregate


class StatTimeseriesFilter(I4cBaseModel):
    """Time series query, filter for Event data types."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Event type.")
    rel: CondEventRel = Field(..., title="Relation.")
    value: str = Field(..., title="Value.")
    age_min: Optional[float] = Field(None, description="In effect for at least this many seconds.")
    age_max: Optional[float] = Field(None, description="In effect for at most this many seconds.")

    @classmethod
    async def load_filters(cls, conn, timeseries):
        sql = "select * from stat_timeseries_filter where timeseries = $1"
        res_d = await conn.fetch(sql, timeseries)
        res = []
        for r in res_d:
            res.append(StatTimeseriesFilter(id=r["id"], device=r["device"], data_id=r["data_id"],
                                            rel=CondEventRel.from_nice_value(r["rel"]), value=r["value"],
                                            age_min=r["age_min"], age_max=r["age_max"]))
        return res

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
                                       self.device, self.data_id, self.rel.nice_value(),
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
    """Time series query, the shown metric (Sample data type)."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Numeric data type.")


class StatTimeseriesSeriesName(str, Enum):
    """Time series query, series naming rule."""
    separator_event = "separator_event"
    sequence = "sequence"
    timestamp = "timestamp"


class StatTimeseriesXAxis(str, Enum):
    """Time series query, X axis."""
    timestamp = "timestamp"
    sequence = "sequence"


class StatTimeseriesSepEvent(I4cBaseModel):
    """Time series query, Event selection."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Event type.")

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        if all(x is not None for x in (d["device"], d["data_id"])):
            return StatTimeseriesSepEvent(device=d["device"], data_id=d["data_id"])
        return None


class StatTimeseriesDef(I4cBaseModel):
    """
    Time series query definition. After and before are exclusive. If both omitted, before defaults to now.
    If before is set, duration is required. If after is set, default duration extends to now.
    """
    after: Optional[datetime] = Field(None, title="Query data after this time.")
    before: Optional[datetime] = Field(None, title="Query data before this time.")
    duration: Optional[str] = Field(None, title="Observed period length.")
    filter: List[StatTimeseriesFilter] = Field(..., title="Event and Condition filters.")
    metric: StatTimeseriesMetric = Field(..., title="The displayed metric, numeric data type.")
    agg_func: Optional[StatAggMethod] = Field(None, title="Aggregation function, if needed.")
    agg_sep: Optional[StatTimeseriesSepEvent] = Field(None, title="Event separating data points, if aggregation is used.")
    series_sep: Optional[StatTimeseriesSepEvent] = Field(None, title="Event separating series, if needed.")
    series_name: Optional[StatTimeseriesSeriesName] = Field(None, title="Rule for naming series.")
    xaxis: StatTimeseriesXAxis = Field(..., title="What is on the x axis.")
    visualsettings: StatVisualSettings = Field(..., title="Chart settings.")

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

        await self.visualsettings.insert_or_update_db(stat_id, conn)

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
                raise I4cServerError("Missing id from StatTimeseriesFilter")
            await conn.execute("delete from stat_timeseries_filter where id = $1", d.id)

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
        d["metric"] = StatTimeseriesMetric(device=d["metric_device"], data_id=d["metric_data_id"])
        d["agg_sep"] = StatTimeseriesSepEvent.create_from_dict(d, "agg_sep_")
        d["series_sep"] = StatTimeseriesSepEvent.create_from_dict(d, "series_sep_")
        d["visualsettings"] = StatVisualSettings.create_from_dict(d, "vs_")
        return StatTimeseriesDef(**d)


class StatTimeseriesDataSeries(I4cBaseModel):
    """
    One data series in a time series query. If the X axis represents time, the values are given in the X properties.
    If the X properties are not given, the X axis should be a sequence. If X values are given, the length of the array
    matches the Y array.
    """
    name: str = Field(..., title="Display name.")
    x_timestamp: Optional[List[datetime]] = Field(None, title="X values if timestamp.")
    x_relative: Optional[List[float]] = Field(None, title="X values, if relative time. Seconds.")
    y: List[float] = Field(..., title="Data points.")


async def statdata_get_timeseries(credentials, st_id:int, st_timeseriesdef: StatTimeseriesDef, conn) -> List[StatTimeseriesDataSeries]:
    after, before = resolve_time_period(st_timeseriesdef.after, st_timeseriesdef.before, st_timeseriesdef.duration)

    total_series = series_intersect.Series()
    total_series.add(series_intersect.TimePeriod(after, before))

    filters = await conn.fetch("select * from stat_timeseries_filter where timeseries = $1", st_id)
    # todo 5: maybe use "timestamp" AND "sequence" for intervals instead of "timestamp" only
    for filter in filters:
        db_series = await conn.fetch(alarm.alarm_check_load_sql, filter["device"], filter["data_id"], after, before)
        current_series = series_intersect.Series()
        for r_series_prev, r_series in prev_iterator(db_series, include_first=False):
            if alarm.check_rel(filter["rel"], filter["value"], r_series_prev["value_text"]):
                age_min = timedelta(seconds=filter["age_min"] if filter["age_min"] and filter["age_min"] > 0 else 0)
                age_max = timedelta(seconds=filter["age_max"]) if filter["age_max"] else None
                if r_series_prev["timestamp"] + age_min < r_series["timestamp"]:
                    if age_max is None or r_series["timestamp"] + age_max > r_series["timestamp"]:
                        t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min,
                                                        r_series["timestamp"])
                    else:
                        t = series_intersect.TimePeriod(r_series_prev["timestamp"] + age_min,
                                                        r_series_prev["timestamp"] + age_max)
                    current_series.add(t)
        total_series = series_intersect.Series.intersect(total_series, current_series)
        del current_series


    def create_StatTimeseriesDataSeries():
        res = StatTimeseriesDataSeries(name="", y=[])
        if st_timeseriesdef.xaxis == StatTimeseriesXAxis.timestamp:
            res.x_relative = []
            res.x_timestamp = []
        return res

    current_series = create_StatTimeseriesDataSeries()
    res = [current_series]
    last_series_sep_value = None

    def record_output(aggregated_value, ts):
        if aggregated_value is None:
            return
        if (current_series.name == "") and st_timeseriesdef.series_name:
            if st_timeseriesdef.series_name == StatTimeseriesSeriesName.separator_event:
                if last_series_sep_value:
                    current_series.name = last_series_sep_value
            elif st_timeseriesdef.series_name == StatTimeseriesSeriesName.sequence:
                current_series.name = str(len(res))
        if current_series.x_timestamp is not None:
            current_series.x_timestamp.append(ts)
            if current_series.x_relative is not None:
                current_series.x_relative.append((ts-current_series.x_timestamp[0]).total_seconds())
        current_series.y.append(aggregated_value)

    if len(total_series) > 0:
        md_series = await conn.fetch(alarm.alarm_check_load_sql,
                                     st_timeseriesdef.metric.device,
                                     st_timeseriesdef.metric.data_id,
                                     total_series[0].start or after,
                                     total_series[-1].end or before)
        agg_sep_ts = []
        if st_timeseriesdef.agg_sep:
            agg_sep_series = await conn.fetch(alarm.alarm_check_load_sql,
                                         st_timeseriesdef.agg_sep.device,
                                         st_timeseriesdef.agg_sep.data_id,
                                         total_series[0].start or after,
                                         total_series[-1].end or before)
            agg_sep_ts = [r["timestamp"] for r in agg_sep_series]

        series_sep_ts = []
        if st_timeseriesdef.series_sep:
            series_sep_series = await conn.fetch(alarm.alarm_check_load_sql,
                                         st_timeseriesdef.series_sep.device,
                                         st_timeseriesdef.series_sep.data_id,
                                         total_series[0].start or after,
                                         total_series[-1].end or before)
            series_sep_ts = [(r["timestamp"], r["value_text"]) for r in series_sep_series]

        agg_values = []
        md_prev = None
        for md_prev, md in prev_iterator(md_series, include_first=False):
            if not total_series.is_timestamp_in(md_prev["timestamp"]):
                continue

            aggregated_value = None
            if st_timeseriesdef.agg_sep:
                while agg_sep_ts and agg_sep_ts[0] < md_prev["timestamp"]:
                    del agg_sep_ts[0]
                if agg_sep_ts and agg_sep_ts[0] < md["timestamp"]:
                    aggregated_value = calc_aggregate(st_timeseriesdef.agg_func, agg_values)
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
                res.append(current_series)

        if agg_values:
            aggregated_value = calc_aggregate(st_timeseriesdef.agg_func, agg_values)
            record_output(aggregated_value, md_prev["timestamp"])

    if st_timeseriesdef.series_name == StatTimeseriesSeriesName.timestamp:
        ts = [(s.x_timestamp[0],s) for s in res if s.x_timestamp]
        tso = optimize_timestamp_label([s[0] for s in ts])
        for s, o in zip(ts, tso):
            s[1].name = o
    return res
