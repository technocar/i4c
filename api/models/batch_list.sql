with
  p as (select 
          $1::varchar(200) -- */ 'proj47'
              as project, 
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  workpiece_begin as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.device = 'lathe'
      and l.data_id='cf'           /* workpiece_begin, todo: use proper data */  
  ), 
  workpiece_end as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.device = 'lathe'
      and l.data_id='ct'           /* workpiece_end, todo: use proper data */  
  ),
  workpiece_id as (
    select l.value_text as "id", wp.batch, l.timestamp, l.sequence
    from log l
    cross join p
    join workpiece wp on wp.id = l.value_text
    where
      l.device = 'lathe'
      and l.data_id='coolhealth'           /* workpiece_id, todo: use proper data */  
      and wp.batch is not null
  ),
  workpiece_project as (
    select l.value_text as "project", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.device = 'lathe'
      and l.data_id='spgm'           /* workpiece_project , todo: use proper data, de ez bonyolultabb lesz:
                                        itt a robot programjának a nevébõl kell majd kikeresni, hogy az melyik project-nek a része  */
  ),
  discover_log as (
    select
      case when we.timestamp is null or we.timestamp>wid.timestamp or (we.timestamp=wid.timestamp and we.sequence>wid.sequence) then wid.id end as id,
      case when we.timestamp is null or we.timestamp>wid.timestamp or (we.timestamp=wid.timestamp and we.sequence>wid.sequence) then wid.batch end as batch,
      wb.timestamp as begin_timestamp,
      we.timestamp as end_timestamp
    from workpiece_id wid
    cross join p
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from workpiece_begin as w
        where 
          w.timestamp < wid.timestamp
          or (w.timestamp = wid.timestamp and w.sequence <= wid.sequence)
      ) a
      where a.r = 1) wb on True
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from workpiece_end as w
        where 
          w.timestamp > wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
      ) a
      where a.r = 1) we on True
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from workpiece_project as w
        where 
          we.timestamp is null
          or w.timestamp < we.timestamp
          or (w.timestamp = we.timestamp and w.sequence <= we.sequence)    
      ) a
      where a.r = 1) wpr on p.project is null or wpr.project = p.project
  ),
  res as (
    select 
      dl.batch,
      min(dl.begin_timestamp) as first,
      max(dl.end_timestamp) as last,
      count(distinct dl.id) as "count"
    from discover_log dl
    group by dl.batch
    order by last desc
  )
select * 
from res
