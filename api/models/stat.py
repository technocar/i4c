# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from textwrap import dedent
from typing import Optional, List, Union
from isodate import ISO8601Error
from pydantic import root_validator, validator, Field
import common.db_helpers
from common import I4cBaseModel, DatabaseConnection, CredentialsAndFeatures, series_intersect, write_debug_sql
import isodate
from common.cmp_list import cmp_list
from common.db_tools import get_user_customer
from common.exceptions import I4cServerError, I4cClientError, I4cClientNotFound
from common.tools import frac_index, optimize_timestamp_label
from models import AlarmCondEventRel, alarm
from models.alarm import prev_iterator
from models.common import PatchResponse
import re


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
    """Time series query, filter for Event data types."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Event type.")
    rel: AlarmCondEventRel = Field(..., title="Relation.")
    value: str = Field(..., title="Value.")
    age_min: Optional[float] = Field(None, description="In effect for at least this many seconds.")
    age_max: Optional[float] = Field(None, description="In effect for at most this many seconds.")

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
    """Time series query, the shown metric (Sample data type)."""
    device: str = Field(..., title="Device.")
    data_id: str = Field(..., title="Numeric data type.")


class StatAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1st"
    q4th = "q4th"
    min = "min"
    max = "max"


class StatTimeseriesSeriesName(str, Enum):
    """Time series query, series naming rule."""
    separator_event = "separator_event"
    sequence = "sequence"
    timestamp = "timestamp"


class StatTimeseriesXAxis(str, Enum):
    """Time series query, X axis."""
    timestamp = "timestamp"
    sequence = "sequence"


class StatTimeseriesType(str, Enum):      # TODO how is this Timeseries?
    timeseries = "timeseries"
    xy = "xy"


class StatSepEvent(I4cBaseModel):      # TODO how is this NOT timeseries?
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
            return StatSepEvent(device=d["device"], data_id=d["data_id"])
        return None


class StatVisualSettingsAxis(I4cBaseModel):
    """Axis settings for charts."""
    caption: Optional[str] = Field(None, title="Caption.")

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        d = defaultdict(lambda: None, **d)
        return StatVisualSettingsAxis(caption=d["caption"])


class StatVisualSettingsLegendPosition(str, Enum):
    """Legend position for charts."""
    Top = 'top'
    Bottom = 'bottom'
    Left = 'left'
    Right = 'right'
    ChartArea = 'chartArea'


class StatVisualSettingsLegendAlign(str, Enum):
    """Legend alingment for charts."""
    Start = 'start'
    Center = 'center'
    End = 'end'


class StatVisualSettingsLegend(I4cBaseModel):
    """Legend settings for charts."""
    position: Optional[StatVisualSettingsLegendPosition]
    align: Optional[StatVisualSettingsLegendAlign]

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        d = defaultdict(lambda: None, **d)
        return StatVisualSettingsLegend(position=d["position"],
                                        align=d["align"])


class StatVisualSettingsTooltip(I4cBaseModel):
    """Tooltip template for charts."""
    html: Optional[str]

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        d = defaultdict(lambda: None, **d)
        return StatVisualSettingsTooltip(html=d["html"])


class StatVisualSettings(I4cBaseModel):
    """Visual settings for charts."""
    title: Optional[str]
    subtitle: Optional[str]
    xaxis: Optional[StatVisualSettingsAxis]
    yaxis: Optional[StatVisualSettingsAxis]
    legend: Optional[StatVisualSettingsLegend]
    tooltip: Optional[StatVisualSettingsTooltip]

    @classmethod
    def create_from_dict(cls, d, prefix):
        if prefix:
            d = {k[len(prefix):]: v for k, v in d.items() if k.startswith(prefix)}
        else:
            d = dict(d)
        d = defaultdict(lambda: None, **d)
        return StatVisualSettings(title=d["title"],
                                  subtitle=d["subtitle"],
                                  xaxis=StatVisualSettingsAxis.create_from_dict(d, "xaxis_"),
                                  yaxis=StatVisualSettingsAxis.create_from_dict(d, "yaxis_"),
                                  legend=StatVisualSettingsLegend.create_from_dict(d, "legend_"),
                                  tooltip=StatVisualSettingsTooltip.create_from_dict(d, "tooltip_"))

    async def insert_or_update_db(self, ts_id, conn):
        exists = await conn.fetchrow("select id from stat_visual_setting where id = $1", ts_id)
        if exists:
            sql = dedent("""\
                update stat_visual_setting
                set
                  title = $2,
                  subtitle = $3,
                  xaxis_caption = $4,
                  yaxis_caption = $5,
                  legend_position = $6,
                  legend_align = $7,
                  tooltip_html = $8
                where id = $1
                """)
        else:
            sql = dedent("""\
                insert into stat_visual_setting (id, title, subtitle,
                                                 xaxis_caption, yaxis_caption, legend_position,
                                                 legend_align, tooltip_html
                                                ) values ($1, $2, $3,
                                                          $4, $5, $6,
                                                          $7, $8)
                """)
        await conn.execute(sql, ts_id, self.title, self.subtitle,
                           self.xaxis.caption if self.xaxis else None,
                           self.yaxis.caption if self.yaxis else None,
                           self.legend.position if self.legend else None,
                           self.legend.align if self.legend else None,
                           self.tooltip.html if self.tooltip else None)


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
    agg_sep: Optional[StatSepEvent] = Field(None, title="Event separating data points, if aggregation is used.")
    series_sep: Optional[StatSepEvent] = Field(None, title="Event separating series, if needed.")
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
        d["agg_sep"] = StatSepEvent.create_from_dict(d, "agg_sep_")
        d["series_sep"] = StatSepEvent.create_from_dict(d, "series_sep_")
        d["visualsettings"] = StatVisualSettings.create_from_dict(d, "vs_")
        return StatTimeseriesDef(**d)


class StatXYObjectType(str, Enum):
    """Virtual object type."""
    workpiece = "workpiece"
    mazakprogram = "mazakprogram"
    mazaksubprogram = "mazaksubprogram"
    batch = "batch"
    tool = "tool"


class StatXYObjectParam(I4cBaseModel):
    """Parameter for parametrized virtual objects."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    key: str
    value: Optional[str]

    @classmethod
    async def load_params(cls, conn, xy_id):
        sql = "select * from stat_xy_object_params where xy = $1"
        res = await conn.fetch(sql, xy_id)
        return [StatXYObjectParam(**r) for r in res]

    async def insert_to_db(self, xy_id, conn):
        sql_insert = dedent("""\
            insert into stat_xy_object_params (xy, key, value)
                values ($1, $2, $3)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, xy_id, self.key, self.value))[0]

    def __eq__(self, other):
        if not isinstance(other, StatXYObjectParam):
            return False
        return ((self.key == other.key)
                and (self.value == other.value))


class StatXYObject(I4cBaseModel):
    """
    Virtual object definition. Virtual objects represent meaningful views of the log, possibly combined with
    user provided metadata. E.g. workpieces, program executions.
    """
    type: StatXYObjectType
    params: List[StatXYObjectParam]


class StatXYOther(I4cBaseModel):
    id: Optional[int] = Field(None, hidden_from_schema=True)
    field_name: str

    @classmethod
    async def load_others(cls, conn, xy_id):
        sql = "select id, field_name from stat_xy_other where xy = $1"
        res = await conn.fetch(sql, xy_id)
        res_b = [StatXYOther(**r) for r in res]
        res_a = [b.field_name for b in res_b]
        return res_a,res_b

    async def insert_to_db(self, xy_id, conn):
        sql_insert = dedent("""\
            insert into stat_xy_other (xy, field_name)
                values ($1, $2)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, xy_id, self.field_name))[0]

    def __eq__(self, other):
        if not isinstance(other, StatXYOther):
            return False
        return self.field_name == other.field_name


class StatXYFilterRel(str, Enum):
    eq = "="
    neq = "!="
    less = "<"
    leq = "<="
    gtr = ">"
    geq = ">="


class StatXYFilter(I4cBaseModel):
    """XY query filter."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    field: str
    rel: StatXYFilterRel
    value: str

    @classmethod
    async def load_filters(cls, conn, xy_id):
        sql = "select * from stat_xy_filter where xy = $1"
        res_d = await conn.fetch(sql, xy_id)
        res = []
        for r in res_d:
            res.append(StatXYFilter(id=r["id"], field=r["field_name"], rel=r["rel"], value=r["value"]))
        return res

    async def insert_to_db(self, xy_id, conn):
        sql_insert = dedent("""\
            insert into stat_xy_filter (xy, field_name, rel, value)
                values ($1, $2, $3, $4)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, xy_id, self.field, self.rel, self.value))[0]

    def __eq__(self, other):
        if not isinstance(other, StatXYFilter):
            return False
        return ((self.field == other.field)
                and (self.rel == other.rel)
                and (self.value == other.value))


class StatXYDef(I4cBaseModel):
    """
    XY query definition. After and before are exclusive. If both omitted, before defaults to now.
    If before is set, duration is required. If after is set, default duration extends to now.
    """
    obj: StatXYObject = Field(..., title="Virtual object to show.")
    after: Optional[datetime] = Field(None, title="Query data after this time.")
    before: Optional[datetime] = Field(None, title="Query data before this time.")
    duration: Optional[str] = Field(None, title="Observed period length.")
    x: str = Field(..., title="Numeric field to show on X axis.")
    y: Optional[str] = Field(None, title="Numeric field to show on Y axis.")
    shape: Optional[str] = Field(None, title="Field to represent as dot shape.")
    color: Optional[str] = Field(None, title="Field to represent as dot color.")
    other: List[str] = Field(..., title="Fields to be used in the tooltip.")
    other_internal: List[StatXYOther] = Field([], hidden_from_schema=True)
    filter: List[StatXYFilter] = Field(..., title="Filters.")
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
        after_s, before_s, duration_s = values.get('after') is not None, values.get('before') is not None, values.get(
            'duration') is not None
        period_s = sum(int(x) for x in (after_s, before_s, duration_s))
        if period_s in (0, 3) or (period_s == 1 and before_s):
            raise ValueError('invalid (after, before, duration) configuration.')
        return values

    async def insert_to_db(self, stat_id, conn):
        sql_insert = dedent("""\
            insert into stat_xy (id,
                                 object_name, after, before,
                                 duration, x_field, y_field,
                                 shape, color)
            select $1,
                   $2, $3, $4,
                   $5::varchar(200)::interval, $6, $7,
                   $8, $9
            """)
        await conn.execute(sql_insert, stat_id, *self.get_sql_params())

        for p in self.obj.params:
            await p.insert_to_db(stat_id, conn)

        for o in self.other:
            await StatXYOther(field_name=o).insert_to_db(stat_id, conn)

        for f in self.filter:
            await f.insert_to_db(stat_id, conn)

        await self.visualsettings.insert_or_update_db(stat_id, conn)


    def get_sql_params(self):
        return [self.obj.type, self.after, self.before,
                self.duration, self.x, self.y,
                self.shape, self.color
                ]

    async def update_to_db(self, stat_id, new_state, conn):
        """
        :param stat_id:
        :param new_state: StatXYDef
        :param conn:
        :return:
        """
        sql_update = dedent("""\
            update stat_xy
            set
              object_name=$2,
              after=$3,
              before=$4,

              duration=$5::varchar(200)::interval,
              x_field=$6,
              y_field=$7,

              shape=$8,
              color=$9
            where id = $1
            """)
        await conn.execute(sql_update, stat_id, *new_state.get_sql_params())

        insert, delete, _, _ = cmp_list(self.obj.params, new_state.obj.params)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatXYObjectParam")
            await conn.execute("delete from stat_xy_object_params where id = $1", d.id)

        new_other = [StatXYOther(field_name=o) for o in new_state.other]
        insert, delete, _, _ = cmp_list(self.other_internal, new_other)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatXYOther")
            await conn.execute("delete from stat_xy_other where id = $1", d.id)

        insert, delete, _, _ = cmp_list(self.filter, new_state.filter)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatXYFilter")
            await conn.execute("delete from stat_xy_filter where id = $1", d.id)

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
        d["obj"] = StatXYObject(type=d["object_name"], params=d["object_param"])
        d["x"] = d["x_field"]
        d["y"] = d["y_field"]
        d["visualsettings"] = StatVisualSettings.create_from_dict(d, "vs_")
        return StatXYDef(**d)


class StatDefIn(I4cBaseModel):
    """Query definition. Input. Exactly one of timeseriesdef or xydef must be given."""
    name: str = Field(..., title="Name.")
    shared: bool = Field(..., title="If set, everyone can run.")
    timeseriesdef: Optional[StatTimeseriesDef] = Field(..., title="Time series definition.")
    xydef: Optional[StatXYDef] = Field(..., title="XY query definition.")

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef_s, xydef_s = values.get('timeseriesdef') is not None, values.get('xydef') is not None
        if sum(int(x) for x in (timeseriesdef_s, xydef_s)) != 1:
            raise ValueError('Exactly one of timeseriesdef or xydef should be present')
        return values


class StatDef(StatDefIn):
    """Query definition. Exactly one of timeseriesdef or xydef is set."""
    id: int = Field(..., title="Identifier.")
    user: StatUser = Field(..., title="Owner of the query.")
    modified: datetime = Field(..., title="Latest modification to the query.")


class StatPatchCondition(I4cBaseModel):
    """Condition for a query definition update."""
    flipped: Optional[bool] = Field(False, title="Pass if the condition is not met.")
    shared: Optional[bool] = Field(None, title="Is shared.")

    def match(self, stat:StatDef):
        r = ((self.shared is None) or (stat.shared == self.shared))

        if self.flipped is None or not self.flipped:
            return r
        else:
            return not r


class StatPatchChange(I4cBaseModel):
    """
    Change to a query. The timeseriesdef and xydef fields must conform with the current type of the query. It is not
    possible to change a query from one type to another.
    """
    shared: Optional[bool] = Field(None, title="Set sharing.")
    timeseriesdef: Optional[StatTimeseriesDef] = Field(None, title="Time series definition.")
    xydef: Optional[StatXYDef] = Field(None, title="XY query definition.")

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef, xydef = values.get('timeseriesdef'), values.get('xydef')
        if timeseriesdef is not None and xydef is not None:
            raise ValueError('timeseriesdef and xydef are exclusive')
        return values

    def is_empty(self):
        return self.timeseriesdef is None and self.xydef is None


class StatPatchBody(I4cBaseModel):
    """Update to a query. All conditions are checked, and passed, the change is carried out."""
    conditions: List[StatPatchCondition] = Field(..., title="Conditions to check before the change.")
    change: StatPatchChange = Field(..., title="Change to the query.")


async def stat_list(credentials: CredentialsAndFeatures, id=None, user_id=None, name=None, name_mask=None,
                    type:Optional[StatTimeseriesType] = None, *, pconn=None) -> List[StatDef]:
    sql = dedent("""\
            with
                res as (
                    select
                      s.id, s."name", s.shared, s.modified, s."customer",

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
                      st.xaxis as st_xaxis,

                      sx.id as sx_id,
                      sx.object_name as sx_object_name,
                      sx.after as sx_after,
                      sx.before as sx_before,
                      sx.duration::varchar(200) as sx_duration,
                      sx.x_field as sx_x_field,
                      sx.y_field as sx_y_field,
                      sx.shape as sx_shape,
                      sx.color as sx_color,

                      vs.title as vs_title,
                      vs.subtitle as vs_subtitle,
                      vs.xaxis_caption as vs_xaxis_caption,
                      vs.yaxis_caption as vs_yaxis_caption,
                      vs.legend_position as vs_legend_position,
                      vs.legend_align as vs_legend_align,
                      vs.tooltip_html as vs_tooltip_html
                    from stat s
                    join "user" u on u.id = s."user"
                    left join "stat_timeseries" st on st."id" = s."id"
                    left join "stat_xy" sx on sx."id" = s."id"
                    left join "stat_visual_setting" vs on vs."id" = s."id"
                    )
            select * from res
            where (res.shared or res.u_id = $1)
          """)
    async with DatabaseConnection(pconn) as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL intervalstyle = 'iso_8601';")
            customer = await get_user_customer(credentials.user_id)
            params = [credentials.user_id]
            if id is not None:
                params.append(id)
                sql += f"and res.id = ${len(params)}\n"
            if customer is not None:
                params.append(customer)
                sql += f"and res.customer = ${len(params)}\n"
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
                timeseriesdef, xydef = None, None
                if d["st_id"] is not None:
                    d["st_filter"] = await StatTimeseriesFilter.load_filters(conn, d["st_id"])
                    timeseriesdef = StatTimeseriesDef.create_from_dict(d,'st_', ['vs_'])
                if d["sx_id"] is not None:
                    d["sx_object_param"] = await StatXYObjectParam.load_params(conn, d["sx_id"])
                    d["sx_other"], d["sx_other_internal"] = await StatXYOther.load_others(conn, d["sx_id"])
                    d["sx_filter"] = await StatXYFilter.load_filters(conn, d["sx_id"])
                    xydef = StatXYDef.create_from_dict(d, 'sx_', ['vs_'])
                res.append(StatDef(**d, timeseriesdef=timeseriesdef, xydef=xydef))
            return res


async def stat_post(credentials:CredentialsAndFeatures, stat: StatDefIn) -> StatDef:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql = "select * from stat where name = $1 and \"user\" = $2"
            old_db = await conn.fetch(sql, stat.name, credentials.user_id)
            if old_db:
                raise I4cClientError("Name already in use")

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
                raise I4cClientNotFound("No record found")
            st = st[0]

            if st.user != credentials.user_id:
                if 'delete any' not in credentials.info_features:
                    raise I4cClientError("Unable to delete other's statistics")

            sql = "delete from stat where id = $1"
            await conn.execute(sql, id)


async def stat_patch(credentials, id, patch:StatPatchBody):
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise I4cClientNotFound("No record found")
            st = st[0]

            if st.user != credentials.user_id:
                if 'patch any' not in credentials.info_features:
                    raise I4cClientError("Unable to modify other's statistics")

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
                    await conn.execute('delete from stat_xy where "id" = $1', st.id)
                if st.timeseriesdef is not None:
                    await st.timeseriesdef.update_to_db(st.id, patch.change.timeseriesdef, conn)
                else:
                    await patch.change.timeseriesdef.insert_to_db(st.id, conn)

            if patch.change.xydef is not None:
                if st.timeseriesdef is not None:
                    await conn.execute('delete from stat_timeseries where "id" = $1', st.id)
                if st.xydef is not None:
                    await st.xydef.update_to_db(st.id, patch.change.xydef, conn)
                else:
                    await patch.change.xydef.insert_to_db(st.id, conn)

            return PatchResponse(changed=True)


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


class StatXYData(I4cBaseModel):
    """One dot in the XY query results."""
    x: Union[float, str, None] = Field(None, title="Value to show on the X axis.")
    y: Optional[Union[float, str, None]] = Field(None, title="Value to show on the Y axis.")
    shape: Optional[Union[float, str, None]] = Field(None, title="Value to show as shape.")
    color: Optional[Union[float, str, None]] = Field(None, title="Value to show as color.")
    others: List[Union[float, str, None]] = Field(..., title="Values to show as tooltip.")


class StatData(I4cBaseModel):
    """Results of a query. Either timeseriesdata or xydata will be given."""
    stat_def: StatDef = Field(..., title="Definition of the query.")
    timeseriesdata: Optional[List[StatTimeseriesDataSeries]] = Field(None, title="Time series results.")
    xydata: Optional[List[StatXYData]] = Field(None, title="XY query results.")


def resolve_time_period(after, before, duration):
    def v(*val):
        return all(x is not None for x in val)

    duration = isodate.parse_duration(duration) if v(duration) else None
    before = before if v(before) else after + duration if v(after, duration) else datetime.now(timezone.utc)
    after = after if v(after) else before - duration
    return after, before


def calc_aggregate(method: StatAggMethod, agg_values, *, from_record=True):
    if from_record:
        agg_values = [v["value_num"] for v in agg_values if v["value_num"] is not None]
    else:
        agg_values = [v for v in agg_values if v is not None]
    if not agg_values:
        return None
    if method == StatAggMethod.avg:
        return sum(v for v in agg_values) / len(agg_values)
    elif method in (StatAggMethod.median, StatAggMethod.q1st, StatAggMethod.q4th):
        o = sorted(v for v in agg_values)
        if method == StatAggMethod.median:
            return frac_index(o, (len(o) - 1) / 2)
        elif method == StatAggMethod.q1st:
            return frac_index(o, (len(o) - 1) / 5)
        elif method == StatAggMethod.q4th:
            return frac_index(o, (len(o) - 1) * 4 / 5)
    elif method == StatAggMethod.min:
        return min(v for v in agg_values)
    elif method == StatAggMethod.max:
        return max(v for v in agg_values)


async def statdata_get_timeseries(credentials, st:StatDef, conn) -> StatData:
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
        if st.timeseriesdef.xaxis == StatTimeseriesXAxis.timestamp:
            res.x_relative = []
            res.x_timestamp = []
        return res

    current_series = create_StatTimeseriesDataSeries()
    res = StatData(stat_def=st, timeseriesdata=[])
    res.timeseriesdata.append(current_series)
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


class StatXYMateFieldType(str, Enum):
    numeric = "numeric"
    category = "category"
    label = "label"


class StatXYMetaFieldUnit(str, Enum):
    percent = "percent"
    second = "second"


class StatXYMetaField(I4cBaseModel):
    """Data field of a virtual object."""
    name: str
    displayname: str
    type: StatXYMateFieldType
    value_list: Optional[List[str]]
    unit: Optional[StatXYMetaFieldUnit]


class StatXYMetaObjectParamType(str, Enum):
    """Data type of a virtual object parameter."""
    int = "int"
    float = "float"
    str = "str"
    datetime = "datetime"


class StatXYMetaObjectParam(I4cBaseModel):
    """Virtual object parameter."""
    name: str
    type: StatXYMetaObjectParamType
    label: str


class StatXYMetaObject(I4cBaseModel):
    """XY query virtual object. Some object types require parameters."""
    name: str = Field(..., title="Internal name.")
    displayname: str = Field(..., title="Display name.")
    fields: List[StatXYMetaField] = Field(..., title="Fields.")
    params: List[StatXYMetaObjectParam] = Field(..., title="Parameters defining the actual objects.")


class StatXYMeta(I4cBaseModel):
    """XY query metadata. Contains information about the available virtual objects and their fields."""
    objects: List[StatXYMetaObject]


class StatXYMazakAxis(str, Enum):
    """Axes of a Mazak machine. X,Y and Z axes are linear, B and C are rotary."""
    x = "x"
    y = "y"
    z = "z"
    b = "b"
    c = "c"


stat_xy_mazak_project_verison_sql = open("models/stat_xy_mazak_project_verison.sql").read()
stat_xy_workpiece_batch_sql = open("models/stat_xy_workpiece_batch.sql").read()


async def get_xymeta(credentials, after: Optional[datetime], *, pconn=None, with_value_list=True) -> StatXYMeta:
    if after is None:
        after = datetime.utcnow() - timedelta(days=365)
    async with DatabaseConnection(pconn) as conn:

        async def get_value_list(sql, *, params=None):
            if not with_value_list:
                return None
            if params is None:
                params = [after]
            return [r[0] for r in await conn.fetch(sql, *params) if r[0] is not None]

        pv_db = (await conn.fetch(stat_xy_mazak_project_verison_sql, after)) if with_value_list else []

        good_bad_list = await get_value_list(dedent("""\
                                select distinct l.value_text
                                from log l
                                where
                                  l.timestamp >= $1
                                  and l.device='gom'
                                  and l.data_id='eval'
                                order by 1
                                """))

        mazak_fields = [
            StatXYMetaField(name="start", displayname="start", type=StatXYMateFieldType.label),
            StatXYMetaField(name="end", displayname="vége", type=StatXYMateFieldType.label),
            StatXYMetaField(name="device", displayname="eszköz", type=StatXYMateFieldType.category,
                            value_list=['mill', 'lathe']),
            StatXYMetaField(name="program", displayname="program", type=StatXYMateFieldType.category,
                            value_list=await get_value_list(dedent("""\
                                select distinct l.value_text
                                from log l
                                where
                                  l.timestamp >= $1
                                  and l.device in ('lathe', 'mill')
                                  and l.data_id='pgm'
                                order by 1
                            """))),
            StatXYMetaField(name="project", displayname="project", type=StatXYMateFieldType.category,
                            value_list=[r["project"] for r in pv_db]),
            StatXYMetaField(name="project version", displayname="project verzió", type=StatXYMateFieldType.category,
                            value_list=[str(r["version"]) for r in pv_db]),
            StatXYMetaField(name="workpiece good/bad", displayname="munkadarab jó/hibás",type=StatXYMateFieldType.category,
                            value_list=good_bad_list),
            StatXYMetaField(name="runtime", displayname="futásidő", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second)
        ]
        for axis in StatXYMazakAxis:
            for agg in StatAggMethod:
                mazak_fields.append(
                    StatXYMetaField(name=f"{agg}_{axis}_load", displayname=f"{agg}_{axis}_load", type=StatXYMateFieldType.numeric))

        mazakprogram = StatXYMetaObject(
            name=StatXYObjectType.mazakprogram,
            displayname="mazakprogram",
            fields=mazak_fields,
            params=[
                StatXYMetaObjectParam(name="age_min", type=StatXYMetaObjectParamType.float, label="futás min (s)"),
                StatXYMetaObjectParam(name="age_max", type=StatXYMetaObjectParamType.float, label="futás max (s)")
            ]
        )

        mazaksubprogram = StatXYMetaObject(**dict(mazakprogram))
        mazaksubprogram.name = StatXYObjectType.mazaksubprogram
        mazaksubprogram.displayname = "mazaksubprogram"
        mazaksubprogram.fields = list(mazak_fields)
        mazaksubprogram.fields.insert(4, StatXYMetaField(name="subprogram", displayname="alprogram", type=StatXYMateFieldType.category,
                                                         value_list=await get_value_list(dedent("""\
                                                             select distinct l.value_text
                                                             from log l
                                                             where
                                                               l.timestamp >= $1
                                                               and l.device in ('lathe', 'mill')
                                                               and l.data_id='spgm'
                                                             order by 1
                                                         """)))
                                      )

        workpiece_fields = [
            StatXYMetaField(name="code", displayname="code", type=StatXYMateFieldType.label),
            StatXYMetaField(name="start", displayname="start", type=StatXYMateFieldType.label),
            StatXYMetaField(name="end", displayname="vége", type=StatXYMateFieldType.label),
            StatXYMetaField(name="batch", displayname="batch", type=StatXYMateFieldType.category,
                            value_list=await get_value_list(stat_xy_workpiece_batch_sql)),
            StatXYMetaField(name="project", displayname="project", type=StatXYMateFieldType.category,
                            value_list=[r["project"] for r in pv_db]),
            StatXYMetaField(name="project version", displayname="project verzió", type=StatXYMateFieldType.category,
                            value_list=[str(r["version"]) for r in pv_db]),
            StatXYMetaField(name="eval", displayname="eval", type=StatXYMateFieldType.category,
                            value_list=good_bad_list),
            StatXYMetaField(name="gom max deviance", displayname="gom max deviance", type=StatXYMateFieldType.numeric),
            StatXYMetaField(name="runtime", displayname="futásidő", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second)
        ]

        sql = dedent("""\
            select distinct m.data_id
            from log l
            join meta m on m.device = l.device and m.data_id = l.data_id
            where
              l.device = 'gom'
              and m.system1 = 'dev'
              and l.timestamp > $1::timestamp with time zone
            order by 1""")

        for r in await conn.fetch(sql, after):
            workpiece_fields.append(StatXYMetaField(name=f"gom {r[0]} deviance", displayname=f"gom {r[0]} deviance", type=StatXYMateFieldType.numeric))

        workpiece = StatXYMetaObject(
            name=StatXYObjectType.workpiece,
            displayname="munkadarab",
            fields=workpiece_fields,
            params=[]
        )

        batch = StatXYMetaObject(
            name=StatXYObjectType.batch,
            displayname="batch",
            fields=[
                StatXYMetaField(name="id", displayname="id", type=StatXYMateFieldType.label),
                StatXYMetaField(name="project", displayname="project", type=StatXYMateFieldType.category,
                                value_list=[r["project"] for r in pv_db]),
                StatXYMetaField(name="project version", displayname="project verzió", type=StatXYMateFieldType.category,
                                value_list=[str(r["version"]) for r in pv_db]),
                StatXYMetaField(name="total wpc count", displayname="munkadarab szám", type=StatXYMateFieldType.numeric),
                StatXYMetaField(name="good wpc count", displayname="munkadarab jó", type=StatXYMateFieldType.numeric),
                StatXYMetaField(name="bad wpc count", displayname="munkadarab hibás", type=StatXYMateFieldType.numeric),
                StatXYMetaField(name="bad percent", displayname="hibás %", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.percent),
                StatXYMetaField(name="time range total", displayname="időtartam", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second),
                StatXYMetaField(name="time per wpc", displayname="idő/db", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second),
                StatXYMetaField(name="time per good", displayname="idő/jó", type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second),
            ],
            params=[]
        )

        tool = StatXYMetaObject(
            name=StatXYObjectType.tool,
            displayname="tool",
            fields=[
                StatXYMetaField(name="id", displayname="id", type=StatXYMateFieldType.label),
                StatXYMetaField(name="type", displayname="típus", type=StatXYMateFieldType.category,
                                value_list=await get_value_list('select distinct "type" from tools order by 1', params=[])),
                StatXYMetaField(name="count used", displayname="használat szám", type=StatXYMateFieldType.numeric),
                StatXYMetaField(name="accumulated cutting time", displayname="össz. használati idő",
                                type=StatXYMateFieldType.numeric, unit=StatXYMetaFieldUnit.second),
            ],
            params=[]
        )

        res = StatXYMeta(objects=[mazakprogram, mazaksubprogram, workpiece, batch, tool])
        return res

stat_xy_mazakprogram_sql = open("models/stat_xy_mazakprogram.sql").read()
stat_xy_mazaksubprogram_sql = open("models/stat_xy_mazaksubprogram.sql").read()
stat_xy_mazakprogram_measure_sql = open("models/stat_xy_mazakprogram_measure.sql").read()
stat_xy_workpiece_sql = open("models/stat_xy_workpiece.sql").read()
stat_xy_workpiece_measure_sql = open("models/stat_xy_workpiece_measure.sql").read()
stat_xy_batch_sql = open("models/stat_xy_batch.sql").read()
stat_xy_tool_sql = open("models/stat_xy_tool.sql").read()


class LoadMeasureItem:
    def __init__(self, timestamp, value_num):
        self.timestamp = timestamp
        self.value_num = value_num


async def load_measure_mazak(conn, after, before, mf_device, measure):
    db_objs = await conn.fetch(stat_xy_mazakprogram_measure_sql, before, after, mf_device, measure)
    write_debug_sql(f"stat_xy_mazakprogram_measure__{mf_device}__{measure}.sql", stat_xy_mazakprogram_measure_sql, before, after, mf_device, measure)
    return [LoadMeasureItem(x["timestamp"], x["value_num"]) for x in db_objs]


async def load_measure_workpiece(conn, after, before, measure):
    db_objs = await conn.fetch(stat_xy_workpiece_measure_sql, before, after, measure)
    write_debug_sql(f"stat_xy_workpiece_measure__{measure}.sql", stat_xy_mazakprogram_measure_sql, before, after, measure)
    return [LoadMeasureItem(x["timestamp"], x["value_num"]) for x in db_objs]


async def statdata_get_xy(credentials, st:StatDef, conn) -> StatData:
    after, before = resolve_time_period(st.xydef.after, st.xydef.before, st.xydef.duration)

    meta = await get_xymeta(credentials, after, pconn=conn)

    res = StatData(stat_def=st, xydata=[])
    meta = [m for m in meta.objects if m.name == st.xydef.obj.type]
    if len(meta) != 1:
        raise I4cClientError("Invalid meta data")
    meta = meta[0]
    if st.xydef.obj.type == StatXYObjectType.mazakprogram:
        sql = stat_xy_mazakprogram_sql
    elif st.xydef.obj.type == StatXYObjectType.mazaksubprogram:
        sql = stat_xy_mazaksubprogram_sql
    elif st.xydef.obj.type == StatXYObjectType.workpiece:
        sql = stat_xy_workpiece_sql
    elif st.xydef.obj.type == StatXYObjectType.batch:
        sql = stat_xy_batch_sql
    elif st.xydef.obj.type == StatXYObjectType.tool:
        sql = stat_xy_tool_sql
    else:
        raise Exception("Not implemented")
    write_debug_sql(f"stat_xy_{st.xydef.obj.type}.sql", sql, before, after)
    db_objs = await conn.fetch(sql, before, after)
    agg_measures = {}

    async def get_field_value(dbo, field_name:str):
        if "mf_"+field_name in dbo:
            return dbo["mf_" + field_name]
        else:
            if st.xydef.obj.type in (StatXYObjectType.mazakprogram, StatXYObjectType.mazaksubprogram):
                return await get_detail_field_mazak(dbo, field_name)
            elif st.xydef.obj.type == StatXYObjectType.workpiece:
                return await get_detail_field_workpiece(dbo, field_name)
            else:
                raise Exception("Invalid field name: " + field_name)

    async def get_detail_field_mazak(dbo, field_name):
        regex = r"(?P<agg>[^_]+)_(?P<axis>[^_]+)_load+"
        match = re.fullmatch(regex, field_name)
        if not match:
            raise Exception("Invalid field name: " + field_name)
        try:
            agg = StatAggMethod[match.group("agg")]
            axis = StatXYMazakAxis[match.group("axis")]
        except KeyError:
            raise Exception("Invalid field name: " + field_name)
        mf_device = dbo["mf_device"]
        mf_start = dbo["mf_start"]
        mf_end = dbo["mf_end"]
        key = (mf_device, axis)
        if key not in agg_measures:
            measure = axis + 'l' if axis != StatXYMazakAxis.b else 'al'
            prods_measure = await load_measure_mazak(conn, after, before, mf_device, measure)
            agg_measures[key] = prods_measure
        prods_measure = agg_measures[key]
        age_min = [x.value for x in st.xydef.obj.params if x.key == "age_min"]
        age_min = timedelta(seconds=float(age_min[0]) if age_min else 0)
        age_max = [x.value for x in st.xydef.obj.params if x.key == "age_max"]
        age_max = timedelta(seconds=float(age_max[0])) if age_max else None
        prod_measure = [x.value_num for x in prods_measure
                        if (mf_start + age_min <= x.timestamp < mf_end
                            and x.timestamp < mf_start + age_max if age_max is not None else True)]
        return calc_aggregate(agg, prod_measure, from_record=False)

    async def get_detail_field_workpiece(dbo, field_name):
        regex = r"gom (?P<measure>.+) deviance"
        match = re.fullmatch(regex, field_name)
        if not match:
            raise Exception("Invalid field name: " + field_name)
        measure = match.group("measure")

        if measure == "max":
            return max(filter(lambda x: x is not None,
                              [await get_detail_field_workpiece(dbo, m.name) for m in meta.fields
                               if re.fullmatch(regex, m.name) and (m.name != field_name)]),
                       default=None)

        mf_start = dbo["mf_start"]
        mf_end = dbo["mf_end"]
        key = measure
        if key not in agg_measures:
            workpieces_measure = await load_measure_workpiece(conn, after, before, measure)
            agg_measures[key] = workpieces_measure
        workpieces_measure = agg_measures[key]
        workpiece_measure = [x for x in workpieces_measure if mf_start <= x.timestamp < mf_end]
        if not workpiece_measure:
            return None
        return max(workpiece_measure, key=lambda x:x.timestamp).value_num


    for dbo in db_objs:
        cox = await get_field_value(dbo, st.xydef.x)
        co = StatXYData(x=cox, others=[])
        if st.xydef.y:
            co.y = await get_field_value(dbo, st.xydef.y)
        if st.xydef.shape:
            co.shape = await get_field_value(dbo, st.xydef.shape)
        if st.xydef.color:
            co.color = await get_field_value(dbo, st.xydef.color)
        for o in st.xydef.other:
            co.others.append(await get_field_value(dbo, o))
        res.xydata.append(co)

    return res


async def statdata_get(credentials, id) -> StatData:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise I4cClientNotFound("No record found")
            st = st[0]
            if st.timeseriesdef is not None:
                return await statdata_get_timeseries(credentials, st, conn)
            elif st.xydef is not None:
                return await statdata_get_xy(credentials, st, conn)
            return StatData()
