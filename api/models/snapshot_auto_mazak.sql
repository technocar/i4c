select
  m.device
from public.minimon_meta m
left join lateral (select * 
       from public.minimon_log lf
       where 
         lf.timestamp <= $1::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
         and lf.device = m.device
         and lf.data_id = m.data_id
       order by lf.timestamp desc, lf."sequence" desc
       limit 1
      ) l on true
where 
  m.data_id = 'exec'
  and l.value_text = 'ACTIVE'
