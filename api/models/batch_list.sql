with
  p as (select 
          $1::varchar(200) -- */ 'A7080'::varchar(200)
              as project, 
          coalesce($2::varchar(200)[]) -- */ array['active', 'closed']::varchar(200)[]
              as "status"
  ),
  workpiece_id as (
    select l.value_text as "id", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.device = 'robot'
      and l.data_id = 'wkpcid'           /* workpiece_id, todo: use proper data */  
  ),
  batch_max as (
    select 
      b.id,
      max(wid.timestamp) as last
    from batch b
    cross join p
    join workpiece w on w.batch = b.id
    cross join lateral (
      select * from (
        select 
          wid.*,
          rank() over (order by wid.timestamp desc, wid.sequence desc) r
        from workpiece_id as wid
        where 
          wid."id" = w."id"
      ) a
      where a.r = 1) wid
    where 
      p.project is null or b.project = p.project
    group by b.id
  )
select
  b.id as batch,
  b.client,
  b.project,
  b.target_count,
  b.status,
  bm.last
from batch b
cross join p
left join batch_max bm on bm.id = b.id
where p."status" is null or (b."status" = any(p."status"))
order by bm.last desc