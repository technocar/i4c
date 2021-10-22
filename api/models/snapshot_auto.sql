with params as (
  select 
    $1::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
      as ts  
)

select
  m.device, l.timestamp, l."sequence"
from public.minimon_meta m
left join lateral (select * 
       from public.minimon_log lf
       where 
         lf.timestamp <= (select ts from params)
         and lf.device = m.device
         and lf.data_id = m.data_id
       order by lf.timestamp desc, lf."sequence" desc
       limit 1
      ) l on true
where 
  m.data_id = 'exec'
  and l.value_text = 'ACTIVE'
  and l.device in ('mill', 'lathe')

union all

select * from (
  select
    l.device, l.timestamp, l."sequence"
  from public.minimon_meta m
  join public.minimon_log l 
      on l.device = m.device
         and l.data_id = m.data_id
  where 
    l.timestamp <= (select ts from params)
    and l.device in ('robot', 'gom')
    and m.category = 'EVENT'
  order by l.timestamp desc, l."sequence" desc
  limit 1
)a

union all

select
  'gom' as device, l.timestamp, l."sequence"
from public.minimon_meta m
left join lateral (select * 
       from public.minimon_log lf
       where 
         lf.timestamp <= (select ts from params)
         and lf.device = m.device
         and lf.data_id = m.data_id
       order by lf.timestamp desc, lf."sequence" desc
       limit 1
      ) l on true
where 
  m.data_id = 'gom'
  and l.value_text = 'STARTED'
  and l.device in ('robot')