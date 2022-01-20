# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from enum import Enum
from textwrap import dedent
from typing import Optional, List, Dict, Union
from pydantic import root_validator, Field
import common.db_helpers
from common import I4cBaseModel, DatabaseConnection, CredentialsAndFeatures
from common.db_tools import get_user_customer
from common.exceptions import I4cClientError, I4cClientNotFound
from models.common import PatchResponse
from .stat_capability import StatCapabilityDef, StatCapabilityFilter, StatCapabilityData, statdata_get_capability, \
    StatCapabilityVisualSettings
from .stat_common import StatObjectParam, StatObjectParamType
from .stat_list import statdata_get_list, StatListDef, StatListOrderBy, StatListFilter, StatListVisualSettings
from .stat_timeseries import StatTimeseriesDef, StatTimeseriesFilter, StatTimeseriesDataSeries, \
    statdata_get_timeseries
from .stat_xy import StatXYDef, StatXYOther, StatXYFilter, StatXYData, statdata_get_xy


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


class StatType(str, Enum):
    timeseries = "timeseries"
    xy = "xy"
    list = "list"


class StatDefIn(I4cBaseModel):
    """Query definition. Input. Exactly one of timeseriesdef or xydef must be given."""
    name: str = Field(..., title="Name.")
    shared: bool = Field(..., title="If set, everyone can run.")
    customer: Optional[str] = Field(None, title="Customer.")
    timeseriesdef: Optional[StatTimeseriesDef] = Field(None, title="Time series definition.")
    capabilitydef: Optional[StatCapabilityDef] = Field(None, title="Capability definition.")
    xydef: Optional[StatXYDef] = Field(None, title="XY query definition.")
    listdef: Optional[StatListDef] = Field(None, title="List query definition.")


    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef_s = values.get('timeseriesdef') is not None
        capabilitydef_s = values.get('capabilitydef') is not None
        xydef_s = values.get('xydef') is not None
        listdef_s = values.get('listdef') is not None
        if sum(int(x) for x in (timeseriesdef_s, capabilitydef_s, xydef_s, listdef_s)) != 1:
            raise ValueError('Exactly one of timeseriesdef, capabilitydef, xydef, or listdef should be present')
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
    customer: Optional[str] = Field(None, title="Customer.")

    def match(self, stat:StatDef):
        r = ( ((self.shared is None) or (stat.shared == self.shared))
              and ((self.customer is None) or (stat.customer == self.customer))
              )

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
    customer: Optional[str] = Field(None, title="Customer.")
    timeseriesdef: Optional[StatTimeseriesDef] = Field(None, title="Time series definition.")
    capabilitydef: Optional[StatCapabilityDef] = Field(None, title="Capability definition.")
    xydef: Optional[StatXYDef] = Field(None, title="XY query definition.")
    listdef: Optional[StatListDef] = Field(None, title="List query definition.")

    @root_validator
    def check_exclusive(cls, values):
        timeseriesdef_s = values.get('timeseriesdef') is not None
        capabilitydef_s = values.get('capabilitydef') is not None
        xydef_s = values.get('xydef') is not None
        listdef_s = values.get('listdef') is not None
        if sum(int(x) for x in (timeseriesdef_s, capabilitydef_s, xydef_s, listdef_s)) > 1:
            raise ValueError('Timeseriesdef, capabilitydef_s, xydef, or listdef are exclusive')
        return values

    def is_empty(self):
        return (self.shared is None
                and self.customer is None
                and self.timeseriesdef is None
                and self.capabilitydef is None
                and self.xydef is None
                and self.listdef is None)


class StatPatchBody(I4cBaseModel):
    """Update to a query. All conditions are checked, and passed, the change is carried out."""
    conditions: List[StatPatchCondition] = Field(..., title="Conditions to check before the change.")
    change: StatPatchChange = Field(..., title="Change to the query.")


async def stat_list(credentials: CredentialsAndFeatures, id=None, user_id=None, name=None, name_mask=None,
                    type:Optional[StatType] = None, *, pconn=None) -> List[StatDef]:
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
                      
                      sc.id as sc_id,
                      sc.after as sc_after,
                      sc.before as sc_before,
                      sc.duration::varchar(200) as sc_duration,
                      sc.metric_device as sc_metric_device,
                      sc.metric_data_id as sc_metric_data_id,
                      sc.nominal as sc_nominal,
                      sc.utl as sc_utl,
                      sc.ltl as sc_ltl,
                      sc.ucl as sc_ucl,
                      sc.lcl as sc_lcl,

                      sx.id as sx_id,
                      sx.object_name as sx_object_name,
                      sx.after as sx_after,
                      sx.before as sx_before,
                      sx.duration::varchar(200) as sx_duration,
                      sx.x_field as sx_x_field,
                      sx.y_field as sx_y_field,
                      sx.shape as sx_shape,
                      sx.color as sx_color,

                      sl.id as sl_id,
                      sl.object_name as sl_object_name,
                      sl.after as sl_after,
                      sl.before as sl_before,
                      sl.duration::varchar(200) as sl_duration,

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
                    left join "stat_capability" sc on sc."id" = s."id"
                    left join "stat_xy" sx on sx."id" = s."id"
                    left join "stat_list" sl on sl."id" = s."id"
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
                if type == StatType.timeseries:
                    sql += f"and res.st_id is not null\n"
                elif type == StatType.xy:
                    sql += f"and res.sx_id is not null\n"
                elif type == StatType.xy:
                    sql += f"and res.sl_id is not null\n"
            res_db = await conn.fetch(sql, *params)
            res = []
            for r in res_db:
                d = dict(r)
                d["user"] = StatUser.create_from_dict(d, 'u_')
                timeseriesdef, capabilitydef, xydef, listdef = None, None, None, None
                if d["st_id"] is not None:
                    d["st_filter"] = await StatTimeseriesFilter.load_filters(conn, d["st_id"])
                    timeseriesdef = StatTimeseriesDef.create_from_dict(d,'st_', ['vs_'])
                if d["sc_id"] is not None:
                    d["sc_filter"] = await StatCapabilityFilter.load_filters(conn, d["sc_id"])
                    d["sc_visualsettings"] = await StatCapabilityVisualSettings.load_settings(conn, d["sc_id"])
                    capabilitydef = StatCapabilityDef.create_from_dict(d,'sc_')
                if d["sx_id"] is not None:
                    d["sx_object_param"] = await StatObjectParam.load_params(conn, d["sx_id"], StatObjectParamType.xy)
                    d["sx_other"], d["sx_other_internal"] = await StatXYOther.load_others(conn, d["sx_id"])
                    d["sx_filter"] = await StatXYFilter.load_filters(conn, d["sx_id"])
                    xydef = StatXYDef.create_from_dict(d, 'sx_', ['vs_'])
                if d["sl_id"] is not None:
                    d["sl_object_param"] = await StatObjectParam.load_params(conn, d["sl_id"], StatObjectParamType.xy)
                    d["sl_order_by"] = await StatListOrderBy.load_order_by(conn, d["sl_id"])
                    d["sl_filter"] = await StatListFilter.load_filters(conn, d["sl_id"])
                    d["sl_visualsettings"] = await StatListVisualSettings.load_settings(conn, d["sl_id"])
                    listdef = StatListDef.create_from_dict(d, 'sl_')
                res.append(StatDef(**d, timeseriesdef=timeseriesdef, capabilitydef=capabilitydef, xydef=xydef, listdef=listdef))
            return res


async def stat_post(credentials:CredentialsAndFeatures, stat: StatDefIn) -> StatDef:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            sql = "select * from stat where name = $1 and \"user\" = $2"
            old_db = await conn.fetch(sql, stat.name, credentials.user_id)
            if old_db:
                raise I4cClientError("Name already in use")

            sql_insert = dedent("""\
                insert into stat (name, "user", shared, customer, modified) values ($1, $2, $3, $4, now())
                returning id
            """)
            stat_id = (await conn.fetchrow(sql_insert, stat.name, credentials.user_id, stat.shared, stat.customer))[0]
            sql_user_name = "select \"name\" from \"user\" where id = $1"
            user_display_name = (await conn.fetchrow(sql_user_name, credentials.user_id))[0]

            if stat.timeseriesdef is not None:
                await stat.timeseriesdef.insert_to_db(stat_id, conn)

            if stat.capabilitydef is not None:
                await stat.capabilitydef.insert_to_db(stat_id, conn)

            if stat.xydef is not None:
                await stat.xydef.insert_to_db(stat_id, conn)

            if stat.listdef is not None:
                await stat.listdef.insert_to_db(stat_id, conn)

            return StatDef(id=stat_id,
                           user=StatUser(id=credentials.user_id, name=user_display_name),
                           modified=datetime.now(timezone.utc),
                           name=stat.name,
                           shared=stat.shared,
                           customer=stat.customer,
                           timeseriesdef=stat.timeseriesdef,
                           capabilitydef=stat.capabilitydef,
                           xydef=stat.xydef,
                           listdef=stat.listdef)


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
            if patch.change.customer is not None:
                params.append(patch.change.customer)
                sql += f",\ncustomer = ${len(params)}"
            sql += "\nwhere id = $1"
            await conn.execute(sql, *params)

            if patch.change.timeseriesdef is not None:
                if st.timeseriesdef is not None:
                    await st.timeseriesdef.update_to_db(st.id, patch.change.timeseriesdef, conn)
                else:
                    await patch.change.timeseriesdef.insert_to_db(st.id, conn)

                if st.capabilitydef is not None:
                    await conn.execute('delete from stat_capability where "id" = $1', st.id)

                if st.xydef is not None:
                    await conn.execute('delete from stat_xy where "id" = $1', st.id)

                if st.listdef is not None:
                    await conn.execute('delete from stat_list where "id" = $1', st.id)

            if patch.change.capabilitydef is not None:
                if st.timeseriesdef is not None:
                    await conn.execute('delete from stat_timeseries where "id" = $1', st.id)

                if st.capabilitydef is not None:
                    await st.capabilitydef.update_to_db(st.id, patch.change.capabilitydef, conn)
                else:
                    await patch.change.capabilitydef.insert_to_db(st.id, conn)

                if st.xydef is not None:
                    await conn.execute('delete from stat_xy where "id" = $1', st.id)
                if st.listdef is not None:
                    await conn.execute('delete from stat_list where "id" = $1', st.id)

            if patch.change.xydef is not None:
                if st.timeseriesdef is not None:
                    await conn.execute('delete from stat_timeseries where "id" = $1', st.id)

                if st.capabilitydef is not None:
                    await conn.execute('delete from stat_capability where "id" = $1', st.id)

                if st.xydef is not None:
                    await st.xydef.update_to_db(st.id, patch.change.xydef, conn)
                else:
                    await patch.change.xydef.insert_to_db(st.id, conn)

                if st.listdef is not None:
                    await conn.execute('delete from stat_list where "id" = $1', st.id)

            if patch.change.listdef is not None:
                if st.timeseriesdef is not None:
                    await conn.execute('delete from stat_timeseries where "id" = $1', st.id)

                if st.capabilitydef is not None:
                    await conn.execute('delete from stat_capability where "id" = $1', st.id)

                if st.xydef is not None:
                    await conn.execute('delete from stat_xy where "id" = $1', st.id)

                if st.listdef is not None:
                    await st.listdef.update_to_db(st.id, patch.change.listdef, conn)
                else:
                    await patch.change.listdef.insert_to_db(st.id, conn)

            return PatchResponse(changed=True)


class StatData(I4cBaseModel):
    """Results of a query. Either timeseriesdata or xydata will be given."""
    stat_def: StatDef = Field(..., title="Definition of the query.")
    timeseriesdata: Optional[List[StatTimeseriesDataSeries]] = Field(None, title="Time series results.")
    capabilitydata: Optional[StatCapabilityData] = Field(None, title="Capability results.")
    xydata: Optional[List[StatXYData]] = Field(None, title="XY query results.")
    listdata: Optional[List[Dict[str, Union[float, str, datetime, None]]]] = Field(None, title="XY query results.")


async def statdata_get(credentials, id) -> StatData:
    async with DatabaseConnection() as conn:
        async with conn.transaction(isolation='repeatable_read'):
            st = await stat_list(credentials, id=id, pconn=conn)
            if len(st) == 0:
                raise I4cClientNotFound("No record found")
            st = st[0]
            res = StatData(stat_def=st)
            if st.timeseriesdef is not None:
                res.timeseriesdata = await statdata_get_timeseries(credentials, st.id, st.timeseriesdef, conn)
            if st.capabilitydef is not None:
                res.capabilitydata = await statdata_get_capability(credentials, st.id, st.capabilitydef, conn)
            elif st.xydef is not None:
                res.xydata = await statdata_get_xy(credentials, st.id, st.xydef, conn)
            elif st.listdef is not None:
                res.listdata = await statdata_get_list(credentials, st.id, st.listdef, conn)
            return res
