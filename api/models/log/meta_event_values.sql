select
  l.data_id, 
  l.value_text "value",
  count(*) "count"
from public.meta m
join public.log l on l.device = m.device and l.data_id = m.data_id
where
  l.timestamp >= $1::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
  and m.category = 'EVENT'
group by l.data_id, l.value_text 
order by 1,2