with
  p as (select 
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  workpiece_begin as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id = 'spotted'
  ), 
  workpiece_end as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id in ('stopped', 'place_good_out', 'place_bad_out')
  ),
  workpiece_id as (
    select l.value_text as "id", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id = 'wkpcid'
  ),
  workpiece_status as (
    select case l.data_id when 'place_good_out' then 'good' else 'bad' end as "auto_status", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id in ('place_good_out', 'place_bad_out')
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
      and l.timestamp <= p.before
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
                 ) mpv on mpv.savepath = 'robot/'||r."program"
                          and mpv.r = 1
  ),
  discover_log as (
    select 
      case when we.timestamp is null or we.timestamp>wid.timestamp or (we.timestamp=wid.timestamp and we.sequence>wid.sequence) then wid.id end as id,
      wb.timestamp as begin_timestamp,
      wb.sequence  as begin_sequence,
      we.timestamp as end_timestamp,
      we.sequence  as end_sequence,
      case when ws.timestamp>wb.timestamp or (ws.timestamp=wb.timestamp and ws.sequence>wb.sequence) then ws."auto_status" end as "auto_status",
      case when wpr.timestamp>wb.timestamp or (wpr.timestamp=wb.timestamp and wpr.sequence>wb.sequence) then wpr."project" end as "project"
    from workpiece_begin wb
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from workpiece_id as w
        where 
          w.timestamp > wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)
      ) a
      where a.r = 1) wid on True
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
        from workpiece_status as w
        where 
          we.timestamp is null
          or w.timestamp < we.timestamp
          or (w.timestamp = we.timestamp and w.sequence <= we.sequence)    
      ) a
      where a.r = 1) ws on True
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
      where a.r = 1) wpr on True
  ),
  res as (
    select 
      discover_log.*,
      wp.batch,
      wp.manual_status,
      coalesce(wp.manual_status,discover_log.auto_status) as "status",
      wpb.customer
    from discover_log
    left join workpiece wp on wp.id = discover_log.id
    left join batch wpb on wpb.id = wp.batch
  )
select * 
from res
where true
