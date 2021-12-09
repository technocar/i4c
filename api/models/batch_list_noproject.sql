with
  p as (select 
          coalesce($1::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  workpiece_id as (
    select l.value_text as "id", wp.batch, l.timestamp, l.sequence
    from log l
    cross join p
    join workpiece wp on wp.id = l.value_text
    where
      l.timestamp >= p.after
      and l.device = 'robot'
      and l.data_id = 'wkpcid'           /* workpiece_id, todo: use proper data */  
      and wp.batch is not null
  )
select 
  a.batch,
  max(a.timestamp) as last
from workpiece_id a
group by a.batch
order by last desc
