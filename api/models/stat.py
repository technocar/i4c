from datetime import datetime
from enum import Enum
from textwrap import dedent
from typing import Optional, List

from fastapi import HTTPException
from isodate import ISO8601Error
from pydantic import root_validator, validator, Field
import common.db_helpers
from common import I4cBaseModel, DatabaseConnection, CredentialsAndFeatures
import isodate
from models import AlarmCondEventRel
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
            """)
        await conn.execute(sql_insert, ts_id,
                           self.device, self.data_id, self.rel,
                           self.value, self.age_min, self.age_max)


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
                                         agg_sep_device, agg_sep_data_id, series_sep_device,
                                         series_sep_data_id, xaxis)
            select $1, 
                   $2, $3, $4::varchar(200)::interval, 
                   $5, $6, $7, 
                   $8, $9, $10, 
                   $11, $12
            """)
        await conn.execute(sql_insert, stat_id, *self.get_sql_params())

        for f in self.filter:
            await f.insert_to_db(stat_id, conn)

    def get_sql_params(self):
        return [self.after, self.before, self.duration,
                self.metric.device, self.metric.data_id, self.agg_func,

                self.agg_sep.device if self.agg_sep is not None else None,
                self.agg_sep.data_id if self.agg_sep is not None else None,
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
              series_sep_device=$10,
              
              series_sep_data_id=$11,
              xaxis=$12
            where id = $1
            """)
        await conn.execute(sql_update, stat_id, *new_state.get_sql_params())

        for f in self.filter:
            # todo: *****************
            # await f.insert_to_db(stat_id, conn)
            pass


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


class StatXYDef(I4cBaseModel):
    # todo 1: **********

    async def insert_to_db(self, conn):
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
                           modified=datetime.now(),
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
