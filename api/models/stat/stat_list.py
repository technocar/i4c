# -*- coding: utf-8 -*-
from collections import namedtuple
import isodate
from isodate import ISO8601Error
from datetime import datetime
from textwrap import dedent
from typing import Optional, List, Union, Dict
from pydantic import root_validator, validator, Field
from common.exceptions import I4cServerError
from common import I4cBaseModel
from common.cmp_list import cmp_list
from .stat_common import StatObject, resolve_time_period, StatObjectParamType
from .stat_virt_obj import StatVirtObjFilterRel, statdata_virt_obj_fields
from functools import total_ordering


class StatListOrderBy(I4cBaseModel):
    id: Optional[int] = Field(None, hidden_from_schema=True)
    field: str
    ascending: Optional[bool] = Field(True, title="sort direction")

    @classmethod
    async def load_order_by(cls, conn, xy_id):
        sql = """select id, field, ascending from stat_list_order_by where "list" = $1 order by sortorder"""
        res = await conn.fetch(sql, xy_id)
        res = [StatListOrderBy(**r) for r in res]
        return res

    async def insert_to_db(self, list_id, conn, sortorder):
        sql_insert = dedent("""\
            insert into stat_list_order_by ("list", field, ascending, sortorder)
                values ($1, $2, $3, $4)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, list_id, self.field, self.ascending, sortorder))[0]

    def __eq__(self, other):
        if not isinstance(other, StatListOrderBy):
            return False
        return ( self.field == other.field
                 and self.ascending == other.ascending
                 )


class StatListFilter(I4cBaseModel):
    """List query filter."""
    id: Optional[int] = Field(None, hidden_from_schema=True)
    field: str
    rel: StatVirtObjFilterRel
    value: str

    @classmethod
    async def load_filters(cls, conn, list_id):
        sql = """select * from stat_list_filter where "list" = $1"""
        res_d = await conn.fetch(sql, list_id)
        res = []
        for r in res_d:
            res.append(StatListFilter(id=r["id"], field=r["field_name"], rel=r["rel"], value=r["value"]))
        return res

    async def insert_to_db(self, list_id, conn):
        sql_insert = dedent("""\
            insert into stat_list_filter ("list", field_name, rel, value)
                values ($1, $2, $3, $4)
            returning id
            """)
        self.id = (await conn.fetchrow(sql_insert, list_id, self.field, self.rel, self.value))[0]

    def __eq__(self, other):
        if not isinstance(other, StatListFilter):
            return False
        return ((self.field == other.field)
                and (self.rel == other.rel)
                and (self.value == other.value))


class StatListVisualSettingsCol(I4cBaseModel):
    """Visual setting col parameter"""
    field: str
    caption: Optional[str]
    width: Optional[int]


class StatListVisualSettings(I4cBaseModel):
    """List settings."""
    title: Optional[str]
    subtitle: Optional[str]
    header_bg: Optional[str]
    header_fg: Optional[str]
    normal_bg: Optional[str]
    normal_fg: Optional[str]
    even_bg: Optional[str]
    even_fg: Optional[str]
    cols: List[StatListVisualSettingsCol]

    @classmethod
    async def load_settings(cls, conn, id):
        sql = f"""select * from stat_list_visual_setting where id = $1"""
        res = await conn.fetchrow(sql, id)
        if res:
            res = StatListVisualSettings(**res, cols=[])
        else:
            res = StatListVisualSettings(cols=[])

        sql = f"""select * from stat_list_visual_setting_col where list = $1 order by sortorder"""
        res_cols = await conn.fetch(sql, id)
        for col in res_cols:
            res.cols.append(StatListVisualSettingsCol(**col))
        return res


    async def insert_or_update_db(self, id, conn):
        exists = await conn.fetchrow("select id from stat_list_visual_setting where id = $1", id)
        if exists:
            sql = dedent("""\
                update stat_list_visual_setting
                set
                  title = $2,
                  subtitle = $3,
                  header_bg = $4, 
                  header_fg = $5,
                  normal_bg = $6,
                  normal_fg = $7,
                  even_bg = $8,
                  even_fg = $9
                where id = $1
                """)
        else:
            sql = dedent("""\
                insert into stat_list_visual_setting (id, title, subtitle,
                                                      header_bg, header_fg, normal_bg,
                                                      normal_fg, even_bg, even_fg
                                                      ) values ($1, $2, $3,
                                                                $4, $5, $6,
                                                                $7, $8, $9)
                """)
        await conn.execute(sql, id, self.title, self.subtitle,
                           self.header_bg, self.header_fg, self.normal_bg,
                           self.normal_fg, self.even_bg, self.even_fg)
        sql_clear_cols = """delete from stat_list_visual_setting_col where list = $1"""
        sql_insert_col = """insert into stat_list_visual_setting_col(list, field, caption, width, sortorder)
                             values ($1, $2, $3, $4, $5)
                          """
        await conn.execute(sql_clear_cols, id)
        for so, col in enumerate(self.cols, start=1):
            await conn.execute(sql_insert_col, id, col.field, col.caption, col.width, so)


class StatListDef(I4cBaseModel):
    """
    List query definition. After and before are exclusive. If both omitted, before defaults to now.
    If before is set, duration is required. If after is set, default duration extends to now.
    """
    obj: StatObject = Field(..., title="Virtual object to show.")
    after: Optional[datetime] = Field(None, title="Query data after this time.")
    before: Optional[datetime] = Field(None, title="Query data before this time.")
    duration: Optional[str] = Field(None, title="Observed period length.")
    order_by: List[StatListOrderBy] = Field([], title="Result ordered by this.")
    filter: List[StatListFilter] = Field(..., title="Filters.")
    visualsettings: StatListVisualSettings = Field(..., title="List settings.")

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

        order_by = values.get('order_by')
        if len(set(s.field for s in order_by)) != len(order_by):
            raise ValueError('duplicates in order_by')

        visualsettingscols = values.get('visualsettings').cols
        if len(set(s.field for s in visualsettingscols)) != len(visualsettingscols):
            raise ValueError('duplicates in visualsettings cols')

        return values

    async def insert_to_db(self, stat_id, conn):
        sql_insert = dedent("""\
            insert into stat_list (id,
                                 object_name, after, before,
                                 duration)
            select $1,
                   $2, $3, $4,
                   $5::varchar(200)::interval
            """)
        await conn.execute(sql_insert, stat_id, *self.get_sql_params())

        for p in self.obj.params:
            await p.insert_to_db(stat_id, conn, StatObjectParamType.list)

        for so, o in enumerate(self.order_by, start=1):
            await o.insert_to_db(stat_id, conn, so)

        for f in self.filter:
            await f.insert_to_db(stat_id, conn)

        await self.visualsettings.insert_or_update_db(stat_id, conn)


    def get_sql_params(self):
        return [self.obj.type, self.after, self.before,
                self.duration
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

              duration=$5::varchar(200)::interval
            where id = $1
            """)
        await conn.execute(sql_update, stat_id, *new_state.get_sql_params())

        insert, delete, _, _ = cmp_list(self.obj.params, new_state.obj.params)
        for f in insert:
            await f.insert_to_db(stat_id, conn, StatObjectParamType.list)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatXYObjectParam")
            await conn.execute("delete from stat_list_object_params where id = $1", d.id)

        insert, delete, _, _ = cmp_list(enumerate(self.order_by, start=1),
                                        enumerate(new_state.order_by, start=1))
        for f in insert:
            await f[1].insert_to_db(stat_id, conn, f[0])
        for d in delete:
            if d[1].id is None:
                raise I4cServerError("Missing id from StatListOrderBy")
            await conn.execute("delete from stat_list_order_by where id = $1", d[1].id)

        insert, delete, _, _ = cmp_list(self.filter, new_state.filter)
        for f in insert:
            await f.insert_to_db(stat_id, conn)
        for d in delete:
            if d.id is None:
                raise I4cServerError("Missing id from StatListFilter")
            await conn.execute("delete from stat_list_filter where id = $1", d.id)

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
        return StatListDef(**d)


@total_ordering
class MinType(object):
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return self is other


async def statdata_get_list(credentials, st_id: int, st_listdef: StatListDef, conn) -> List[Dict[str, Union[float, str, None]]]:
    after, before = resolve_time_period(st_listdef.after, st_listdef.before, st_listdef.duration)
    db_objs, get_field_value = await statdata_virt_obj_fields(credentials, after, before, st_listdef.obj, conn)

    result_row = namedtuple('result_row', ['content', 'order'])

    grid = []
    for dbo in db_objs:
        agg_measures = {}
        co = result_row({}, [])
        for c in st_listdef.visualsettings.cols:
            co.content[c.field] = await get_field_value(dbo, c.field, agg_measures)
        for c in st_listdef.order_by:
            co.order.append(await get_field_value(dbo, c.field, agg_measures))
        grid.append(co)

    Min = MinType()
    for idx, c in reversed(list(enumerate(st_listdef.order_by))):
        grid = sorted(grid, key=lambda x: Min if x.order[idx] is None else x.order[idx], reverse=not c.ascending)

    return [r.content for r in grid]
