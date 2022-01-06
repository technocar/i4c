with
  p as (select
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after,
          $3::varchar(200) -- */ 'xl'::varchar(200)
              as meas
  )
select l.timestamp, l.value_num
from log l
cross join p
where
  l.timestamp >= p.after
  and l.timestamp <= p.before
  and l.device = 'gom'
  and l.data_id = p.meas
