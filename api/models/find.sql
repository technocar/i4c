select 
  a.timestamp
from (
  select
    /*m.data_id,
    m.name,
    m.nice_name,
    m.system1,
    m.system2,
    m.category,
    m.type,
    m.subtype,
    m.unit,
    l.value_num,
    l.value_text,
    l.value_extra,
    l.value_aux,*/
    l.timestamp,
    rank() over (order by l.timestamp <rank_direction>, l."sequence" <rank_direction>) "#r"
  from public.minimon_meta m
  join public.minimon_log l on l.device = m.device and l.data_id = m.data_id
  where m.device = $1 -- 'lathe'
<wheres>
) a
where a."#r" = 1