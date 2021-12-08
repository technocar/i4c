with
  p as (select
          coalesce($1::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  p_begin as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.device = 'robot'
      and l.data_id = 'spotted'
  ), 
  p_code as (
    select l.value_text as "code", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.device = 'robot'
      and l.data_id = 'wkpcid'
  ),
  p_batch as (
    select w.batch, p_code.timestamp, p_code.sequence
    from workpiece w
    join p_code on p_code."code" = w.id
  )
select distinct 
  w_batch."batch"
from p_begin wb
left join lateral (
  select * from (
  select 
    w.*,
    rank() over (order by w.timestamp asc, w.sequence asc) r
  from p_batch as w
  where
    w.timestamp > wb.timestamp
    or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
  ) a
  where a.r = 1) w_batch on True