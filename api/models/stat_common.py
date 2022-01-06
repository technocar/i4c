# -*- coding: utf-8 -*-
from collections import defaultdict
import isodate
from datetime import datetime, timezone
from enum import Enum
from textwrap import dedent
from typing import Optional, List
from pydantic import Field
from common import I4cBaseModel
from common.tools import frac_index


class StatAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1st"
    q4th = "q4th"
    min = "min"
    max = "max"


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


class StatObjectType(str, Enum):
    """Virtual object type."""
    workpiece = "workpiece"
    mazakprogram = "mazakprogram"
    mazaksubprogram = "mazaksubprogram"
    batch = "batch"
    tool = "tool"


class StatObjectParam(I4cBaseModel):
    """Parameter for parametrized virtual objects."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    key: str
    value: Optional[str]

    @classmethod
    async def load_params(cls, conn, xy_id):
        sql = "select * from stat_xy_object_params where xy = $1"
        res = await conn.fetch(sql, xy_id)
        return [StatObjectParam(**r) for r in res]

    async def insert_to_db(self, xy_id, conn):
        sql_insert = dedent("""\
            insert into stat_xy_object_params (xy, key, value)
                values ($1, $2, $3)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, xy_id, self.key, self.value))[0]

    def __eq__(self, other):
        if not isinstance(other, StatObjectParam):
            return False
        return ((self.key == other.key)
                and (self.value == other.value))


class StatObject(I4cBaseModel):
    """
    Virtual object definition. Virtual objects represent meaningful views of the log, possibly combined with
    user provided metadata. E.g. workpieces, program executions.
    """
    type: StatObjectType
    params: List[StatObjectParam]


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
