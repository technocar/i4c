from datetime import datetime
from enum import Enum
from typing import Optional, List

from isodate import ISO8601Error
from pydantic import root_validator, validator, Field
from common import I4cBaseModel, DatabaseConnection
import isodate

from models import AlarmCondEventRel


class StatUser(I4cBaseModel):
    id: int
    name: str


class StatTimeseriesFilter(I4cBaseModel):
    """ category="EVENT" only """
    device: str
    data_id: str
    rel: AlarmCondEventRel
    value: str
    age_min: Optional[float] = Field(None, description="sec")
    age_max: Optional[float] = Field(None, description="sec")


class StatTimeseriesMetric(I4cBaseModel):
    """ category="SAMPLE" only """
    device: str
    data_id: str


class StatTimeseriesAggMethod(str, Enum):
    avg = "avg"
    median = "median"
    q1st = "q1th"
    q4th = "q4th"
    min = "min"
    max = "max"


class StatTimeseriesXAxis(str, Enum):
    timestamp = "timestamp"
    sequence = "sequence"


class StatSepEvent(I4cBaseModel):
    """ category="EVENT" only """
    device: str
    data_id: str


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


class StatXYDef(I4cBaseModel):
    # todo 1: **********
    pass


class StatDefIn(I4cBaseModel):
    name: str
    shared: bool
    timeseriesdef: Optional[StatTimeseriesDef]
    xydef: Optional[StatXYDef]

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef, xydef = values.get('timeseriesdef'), values.get('xydef')
        if timeseriesdef is not None and xydef is not None:
            raise ValueError('timeseriesdef and xydef are exclusive')
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


async def stat_list(credentials, id=None, user=None, name=None, name_mask=None, type=None, *, pconn=None):
    # todo 1: **********
    pass


async def stat_post(credentials, stat):
    # todo 1: **********
    pass


async def stat_delete(credentials, id):
    # todo 1: **********
    pass


async def stat_patch(credentials, id, patch:StatPatchBody):
    # todo 1: **********
    pass
