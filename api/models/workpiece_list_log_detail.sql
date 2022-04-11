with
  p as (select 
       coalesce($1::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
           as after_ts,
       coalesce($2::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
           as before_ts
  )
select 
  l.device,
  l.timestamp as ts, 
  l.sequence as seq,
  l.data_id as data,
  l.value_text as "text",
  l.value_extra
from meta m
join log l on l.device = m.device and l.data_id = m.data_id
cross join p
where
  l.timestamp >= p.after_ts
  and l.timestamp <= p.before_ts
  and m.category != 'SAMPLE'
order by 
  l.timestamp, 
  l.sequence
