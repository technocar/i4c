select
  l.timestamp,
  l.sequence,
  m.device,
  m.data_id,
  l.value_num,
  l.value_text,
  l.value_extra,
  l.value_aux  
from public.minimon_meta m
join public.minimon_log l on l.device = m.device and l.data_id = m.data_id
where m.device = $1 -- 'lathe'
<wheres>
order by l.timestamp <rank_direction>, l."sequence" <rank_direction>
limit <count>