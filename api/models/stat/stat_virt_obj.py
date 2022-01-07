# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from enum import Enum
from textwrap import dedent
from typing import Optional, List
from pydantic import Field
from common import DatabaseConnection, write_debug_sql
from common import I4cBaseModel
from .stat_common import StatAggMethod, StatObjectType


class StatObjMateFieldType(str, Enum):
    numeric = "numeric"
    category = "category"
    label = "label"


class StatObjMetaFieldUnit(str, Enum):
    percent = "percent"
    second = "second"


class StatObjMetaField(I4cBaseModel):
    """Data field of a virtual object."""
    name: str
    displayname: str
    type: StatObjMateFieldType
    value_list: Optional[List[str]]
    unit: Optional[StatObjMetaFieldUnit]


class StatObjMetaParamType(str, Enum):
    """Data type of a virtual object parameter."""
    int = "int"
    float = "float"
    str = "str"
    datetime = "datetime"


class StatObjMetaParam(I4cBaseModel):
    """Virtual object parameter."""
    name: str
    type: StatObjMetaParamType
    label: str


class StatMetaObject(I4cBaseModel):
    """XY query virtual object. Some object types require parameters."""
    name: str = Field(..., title="Internal name.")
    displayname: str = Field(..., title="Display name.")
    fields: List[StatObjMetaField] = Field(..., title="Fields.")
    params: List[StatObjMetaParam] = Field(..., title="Parameters defining the actual objects.")


class StatObjMazakAxis(str, Enum):
    """Axes of a Mazak machine. X,Y and Z axes are linear, B and C are rotary."""
    x = "x"
    y = "y"
    z = "z"
    b = "b"
    c = "c"


stat_obj_mazak_project_verison_sql = open("models/stat/stat_obj_mazak_project_verison.sql").read()
stat_obj_workpiece_batch_sql = open("models/stat/stat_obj_workpiece_batch.sql").read()


async def get_objmeta(credentials, after: Optional[datetime], *, pconn=None, with_value_list=True) -> List[StatMetaObject]:
    if after is None:
        after = datetime.utcnow() - timedelta(days=365)
    async with DatabaseConnection(pconn) as conn:

        async def get_value_list(sql, *, params=None):
            if not with_value_list:
                return None
            if params is None:
                params = [after]
            return [r[0] for r in await conn.fetch(sql, *params) if r[0] is not None]

        pv_db = (await conn.fetch(stat_obj_mazak_project_verison_sql, after)) if with_value_list else []

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
            StatObjMetaField(name="start", displayname="start", type=StatObjMateFieldType.label),
            StatObjMetaField(name="end", displayname="vége", type=StatObjMateFieldType.label),
            StatObjMetaField(name="device", displayname="eszköz", type=StatObjMateFieldType.category,
                             value_list=['mill', 'lathe']),
            StatObjMetaField(name="program", displayname="program", type=StatObjMateFieldType.category,
                             value_list=await get_value_list(dedent("""\
                                select distinct l.value_text
                                from log l
                                where
                                  l.timestamp >= $1
                                  and l.device in ('lathe', 'mill')
                                  and l.data_id='pgm'
                                order by 1
                            """))),
            StatObjMetaField(name="project", displayname="project", type=StatObjMateFieldType.category,
                             value_list=[r["project"] for r in pv_db]),
            StatObjMetaField(name="project version", displayname="project verzió", type=StatObjMateFieldType.category,
                             value_list=[str(r["version"]) for r in pv_db]),
            StatObjMetaField(name="workpiece good/bad", displayname="munkadarab jó/hibás", type=StatObjMateFieldType.category,
                             value_list=good_bad_list),
            StatObjMetaField(name="runtime", displayname="futásidő", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second)
        ]
        for axis in StatObjMazakAxis:
            for agg in StatAggMethod:
                mazak_fields.append(
                    StatObjMetaField(name=f"{agg}_{axis}_load", displayname=f"{agg}_{axis}_load", type=StatObjMateFieldType.numeric))

        mazakprogram = StatMetaObject(
            name=StatObjectType.mazakprogram,
            displayname="mazakprogram",
            fields=mazak_fields,
            params=[
                StatObjMetaParam(name="age_min", type=StatObjMetaParamType.float, label="futás min (s)"),
                StatObjMetaParam(name="age_max", type=StatObjMetaParamType.float, label="futás max (s)")
            ]
        )

        mazaksubprogram = StatMetaObject(**dict(mazakprogram))
        mazaksubprogram.name = StatObjectType.mazaksubprogram
        mazaksubprogram.displayname = "mazaksubprogram"
        mazaksubprogram.fields = list(mazak_fields)
        mazaksubprogram.fields.insert(4, StatObjMetaField(name="subprogram", displayname="alprogram", type=StatObjMateFieldType.category,
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
            StatObjMetaField(name="code", displayname="code", type=StatObjMateFieldType.label),
            StatObjMetaField(name="start", displayname="start", type=StatObjMateFieldType.label),
            StatObjMetaField(name="end", displayname="vége", type=StatObjMateFieldType.label),
            StatObjMetaField(name="batch", displayname="batch", type=StatObjMateFieldType.category,
                             value_list=await get_value_list(stat_obj_workpiece_batch_sql)),
            StatObjMetaField(name="project", displayname="project", type=StatObjMateFieldType.category,
                             value_list=[r["project"] for r in pv_db]),
            StatObjMetaField(name="project version", displayname="project verzió", type=StatObjMateFieldType.category,
                             value_list=[str(r["version"]) for r in pv_db]),
            StatObjMetaField(name="eval", displayname="eval", type=StatObjMateFieldType.category,
                             value_list=good_bad_list),
            StatObjMetaField(name="gom max deviance", displayname="gom max deviance", type=StatObjMateFieldType.numeric),
            StatObjMetaField(name="runtime", displayname="futásidő", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second)
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
            workpiece_fields.append(StatObjMetaField(name=f"gom {r[0]} deviance", displayname=f"gom {r[0]} deviance", type=StatObjMateFieldType.numeric))

        workpiece = StatMetaObject(
            name=StatObjectType.workpiece,
            displayname="munkadarab",
            fields=workpiece_fields,
            params=[]
        )

        batch = StatMetaObject(
            name=StatObjectType.batch,
            displayname="batch",
            fields=[
                StatObjMetaField(name="id", displayname="id", type=StatObjMateFieldType.label),
                StatObjMetaField(name="project", displayname="project", type=StatObjMateFieldType.category,
                                 value_list=[r["project"] for r in pv_db]),
                StatObjMetaField(name="project version", displayname="project verzió", type=StatObjMateFieldType.category,
                                 value_list=[str(r["version"]) for r in pv_db]),
                StatObjMetaField(name="total wpc count", displayname="munkadarab szám", type=StatObjMateFieldType.numeric),
                StatObjMetaField(name="good wpc count", displayname="munkadarab jó", type=StatObjMateFieldType.numeric),
                StatObjMetaField(name="bad wpc count", displayname="munkadarab hibás", type=StatObjMateFieldType.numeric),
                StatObjMetaField(name="bad percent", displayname="hibás %", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.percent),
                StatObjMetaField(name="time range total", displayname="időtartam", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second),
                StatObjMetaField(name="time per wpc", displayname="idő/db", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second),
                StatObjMetaField(name="time per good", displayname="idő/jó", type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second),
            ],
            params=[]
        )

        tool = StatMetaObject(
            name=StatObjectType.tool,
            displayname="tool",
            fields=[
                StatObjMetaField(name="id", displayname="id", type=StatObjMateFieldType.label),
                StatObjMetaField(name="type", displayname="típus", type=StatObjMateFieldType.category,
                                 value_list=await get_value_list('select distinct "type" from tools order by 1', params=[])),
                StatObjMetaField(name="count used", displayname="használat szám", type=StatObjMateFieldType.numeric),
                StatObjMetaField(name="accumulated cutting time", displayname="össz. használati idő",
                                 type=StatObjMateFieldType.numeric, unit=StatObjMetaFieldUnit.second),
            ],
            params=[]
        )

        return [mazakprogram, mazaksubprogram, workpiece, batch, tool]


stat_obj_mazakprogram_sql = open("models/stat/stat_obj_mazakprogram.sql").read()
stat_obj_mazaksubprogram_sql = open("models/stat/stat_obj_mazaksubprogram.sql").read()
stat_obj_mazakprogram_measure_sql = open("models/stat/stat_obj_mazakprogram_measure.sql").read()
stat_obj_workpiece_sql = open("models/stat/stat_obj_workpiece.sql").read()
stat_obj_workpiece_measure_sql = open("models/stat/stat_obj_workpiece_measure.sql").read()
stat_obj_batch_sql = open("models/stat/stat_obj_batch.sql").read()
stat_obj_tool_sql = open("models/stat/stat_obj_tool.sql").read()


class LoadMeasureItem:
    def __init__(self, timestamp, value_num):
        self.timestamp = timestamp
        self.value_num = value_num


async def load_measure_mazak(conn, after, before, mf_device, measure):
    db_objs = await conn.fetch(stat_obj_mazakprogram_measure_sql, before, after, mf_device, measure)
    write_debug_sql(f"stat_xy_mazakprogram_measure__{mf_device}__{measure}.sql", stat_obj_mazakprogram_measure_sql, before, after, mf_device, measure)
    return [LoadMeasureItem(x["timestamp"], x["value_num"]) for x in db_objs]


async def load_measure_workpiece(conn, after, before, measure):
    db_objs = await conn.fetch(stat_obj_workpiece_measure_sql, before, after, measure)
    write_debug_sql(f"stat_xy_workpiece_measure__{measure}.sql", stat_obj_mazakprogram_measure_sql, before, after, measure)
    return [LoadMeasureItem(x["timestamp"], x["value_num"]) for x in db_objs]
