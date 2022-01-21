select
  m.data_id,
  coalesce(m.name,m.data_id) as name,
  coalesce(m.nice_name,m.name,m.data_id) as nice_name,
  l.value_text as value,
  l.timestamp
from meta m
join log l on l.device = m.device and l.data_id = m.data_id
where 
  l.device = $1 -- */ 'lathe'
  and l.timestamp <= $2::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
  and l.data_id in ('estop', 'ln', 'mode', 'pfo', 'pfr', 'rf', 'Sovr', 'pc')
order by l.timestamp desc, l."sequence" desc
limit 20