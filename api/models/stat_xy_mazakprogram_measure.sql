with
  p as (select
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after,
          coalesce($3::double precision,0::double precision) -- */ 0::double precision
              as age_min,
          $4::double precision -- */ null::double precision
              as age_max,
          $5::varchar(200) -- */ 'lathe'::varchar(200)
              as device,
          $6::varchar(200) -- */ 'xl'::varchar(200)
              as meas
  )
select l.device, l.value_num, l.timestamp, l.sequence
from log l
cross join p
where
  l.timestamp >= p.after + p.age_min * '1 sec'::interval
  and ( p.age_max is null 
        or l.timestamp <= p.after + p.age_max * '1 sec'::interval)
  and l.timestamp <= p.before
  and l.device = p.device
  and l.data_id = p.meas
