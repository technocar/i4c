select
  m.data_id,
  coalesce(m.name,m.data_id) as name,
  coalesce(m.nice_name,m.name,m.data_id) as nice_name,
  m.system1,
  m.system2,
  m.category,
  m.type,
  m.subtype,
  m.unit,
  l.value_num,
  l.value_text,
  l.value_extra,
  l.value_aux,
  l.timestamp
from public.meta m
left join lateral (select * 
       from public.log lf
       where 
         lf.timestamp <= $2::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
         and lf.device = m.device
         and lf.data_id = m.data_id
       order by lf.timestamp desc, lf."sequence" desc
       limit 1
      ) l on true
where m.device = $1 -- */ 'lathe'
