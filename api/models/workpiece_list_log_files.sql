with
  p as (select 
       coalesce($1::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
           as after_ts,
       coalesce($2::int,0) -- */ 0
           as after_seq,
       coalesce($3::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
           as before_ts,
       coalesce($4::int,0) -- */ 0
           as before_seq
  )
select 
  l.value_text as "download_name"
from log l
cross join p
where
  ( l.timestamp > p.after_ts
    or (l.timestamp = p.after_ts and (l.sequence > p.after_seq or p.after_seq is null))
  ) 
  and ( l.timestamp < p.before_ts
    or (l.timestamp = p.before_ts and (l.sequence < p.before_seq or p.before_seq is null))
  )
  and l.device = 'gom' and l.data_id = 'file'
order by 
  l.timestamp, 
  l.sequence
