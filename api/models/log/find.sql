select
  l.timestamp,
  l.sequence,
  m.device,
  l.instance,
  m.data_id,
  case when m.category='SAMPLE' THEN l.value_num::character varying(200) else l.value_text end as "value",
  l.value_num,
  l.value_text,
  l.value_extra,
  l.value_aux as value_add
from meta m
join log l on l.device = m.device and l.data_id = m.data_id
where m.device = $1 -- 'lathe'
<wheres>
order by l.timestamp <rank_direction>, l."sequence" <rank_direction>
limit <count>