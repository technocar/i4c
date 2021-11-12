from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field, root_validator
from common.exceptions import I4cInputValidationError
from common import I4cBaseModel, DatabaseConnection


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

    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('aggregate_period') is None else 0
        x += 1 if values.get('aggregate_count') is None else 0
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


class AlarmCondCondition(I4cBaseModel):
    device: str
    data_id: str
    value: str
    age_min: Optional[float] = Field(None, description="sec")


class AlarmCond(I4cBaseModel):
    sample: AlarmCondSample
    event: AlarmCondEvent
    condition: AlarmCondCondition

    @root_validator
    def check_exclusive(cls, values):
        x = 1 if values.get('sample') is None else 0
        x += 1 if values.get('event') is None else 0
        x += 1 if values.get('condition') is None else 0
        if x > 1:
            raise I4cInputValidationError('sample, event, and condition are exclusive')
        if x == 0:
            raise I4cInputValidationError('sample, event, or condition are required')
        return values


class AlarmDefIn(I4cBaseModel):
    name: str
    conditions: List[AlarmCond]
    max_freq: Optional[float] = Field(None, description="sec")


class AlarmDef(AlarmDefIn):
    last_check: datetime
    last_report: datetime


async def alarmdef_get(credentials, name):
    # todo 1: **********
    pass
