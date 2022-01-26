# -*- coding: utf-8 -*-
import isodate
from isodate import ISO8601Error
from datetime import datetime
from textwrap import dedent
from typing import Optional, List, Union
from pydantic import root_validator, validator, Field
from common.exceptions import I4cServerError
from common import I4cBaseModel
from common.cmp_list import cmp_list
from .stat_common import StatObject, StatVisualSettings, resolve_time_period, StatObjectParamType
from .stat_virt_obj import StatVirtObjFilterRel, statdata_virt_obj_fields


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


class StatXYFilter(I4cBaseModel):
    """XY query filter."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    field: str
    rel: StatVirtObjFilterRel
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
    obj: StatObject = Field(..., title="Virtual object to show.")
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
            await p.insert_to_db(stat_id, conn, StatObjectParamType.xy)

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
            await f.insert_to_db(stat_id, conn, StatObjectParamType.xy)
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
        d["obj"] = StatObject(type=d["object_name"], params=d["object_param"])
        d["x"] = d["x_field"]
        d["y"] = d["y_field"]
        d["visualsettings"] = StatVisualSettings.create_from_dict(d, "vs_")
        return StatXYDef(**d)


class StatXYData(I4cBaseModel):
    """One dot in the XY query results."""
    x: Union[float, str, None] = Field(None, title="Value to show on the X axis.")
    y: Optional[Union[float, str, None]] = Field(None, title="Value to show on the Y axis.")
    shape: Optional[Union[float, str, None]] = Field(None, title="Value to show as shape.")
    color: Optional[Union[float, str, None]] = Field(None, title="Value to show as color.")
    others: List[Union[float, str, datetime, None]] = Field(..., title="Values to show as tooltip.")


async def statdata_get_xy(credentials, st_id: int, st_xydef: StatXYDef, conn) -> List[StatXYData]:
    res = []
    after, before = resolve_time_period(st_xydef.after, st_xydef.before, st_xydef.duration)
    db_objs, get_field_value = await statdata_virt_obj_fields(credentials, after, before, st_xydef.obj, conn)

    agg_measures = {}
    for dbo in db_objs:
        cox = await get_field_value(dbo, st_xydef.x, agg_measures)
        co = StatXYData(x=cox, others=[])
        if st_xydef.y:
            co.y = await get_field_value(dbo, st_xydef.y, agg_measures)
        if st_xydef.shape:
            co.shape = await get_field_value(dbo, st_xydef.shape, agg_measures)
        if st_xydef.color:
            co.color = await get_field_value(dbo, st_xydef.color, agg_measures)
        for o in st_xydef.other:
            co.others.append(await get_field_value(dbo, o, agg_measures))
        res.append(co)

    return res
