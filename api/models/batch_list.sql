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
      l.timestamp >= p.after
      and l.device = 'robot'
      and l.data_id = 'spotted'           /* workpiece_begin, todo: use proper data */  
  ), 
  workpiece_end as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.device = 'robot'
      and l.data_id in ('place_good_out', 'place_bad_out')   /* workpiece_end, todo: use proper data */  
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
  ),
  map_project_version as (
    select
      f.savepath,
      i.timestamp, 
      i.project, 
      i.real_version as version
    from installation_file f
    join installation i on i.id = f.installation  
  ),
  robot_program as (
    select l.value_text as "program", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.device='robot'
      and l.data_id='pgm'
  ),
  workpiece_project as (
    select mpv."project", mpv.version, r.timestamp, r.sequence
    from robot_program r
    join lateral (select 
                    m.*,
                    rank() over (order by m.timestamp desc) r
                  from map_project_version m
                  where 
                    m.timestamp <= r.timestamp
                 ) mpv on mpv.savepath = 'robot/'||r."program"   /* todo: use proper path */
                          and mpv.r = 1
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
      max(coalesce(dl.begin_timestamp, dl.end_timestamp)) as last
    from discover_log dl
    where dl.batch is not null
    group by dl.batch
    order by last desc
  )
select * 
from res
