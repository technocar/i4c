with
  p as (select
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  p_begin as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id = 'wkpcid'
  ), 
  p_end as (
    select l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id = 'state'
      and l.value_text in ('stopped', 'place_good_out', 'place_bad_out')
  ),
  p_code as (
    select l.value_text as "code", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device = 'robot'
      and l.data_id = 'wkpcid'
  ),
  p_batch as (
    select w.batch, p_code.timestamp, p_code.sequence
    from workpiece w
    join p_code on p_code."code" = w.id
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
  p_project_version as (
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
  workpiece_gb as (
    select case l.value_text when 'place_good_out' then 'good' when 'place_bad_out' then 'bad' else 'unknown' end as gb, l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device='robot'
      and l.data_id = 'status'
      and l.value_text in ('place_good_out', 'place_bad_out', 'stopped')
  ),
  discover_log as (
    select 
      wb.timestamp as mf_start,
      we.timestamp as mf_end,
      w_code."code" as mf_code,
      w_batch."batch" as mf_batch,
      w_project."project" as mf_project,
      w_project."version" as "mf_project version",
      w_gb.gb as "mf_workpiece good/bad"
    from p_begin wb
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from p_end as w
        where
          w.timestamp > wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
      ) a
      where a.r = 1) we on True
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from p_code as w
        where
          w.timestamp > wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
      ) a
      where a.r = 1) w_code on True
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
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from p_project_version as w
        where
          w.timestamp < wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence <= wb.sequence)    
      ) a
      where a.r = 1) w_project on True
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from workpiece_gb as w
        left join (
          select * from (
            select 
              *,
              rank() over (order by r.timestamp asc, r.sequence asc) r
            from robot_program r 
            where 
              r.timestamp > wb.timestamp
              or (r.timestamp = wb.timestamp and r.sequence >= wb.sequence)   
          ) a 
          where a.r = 1
        ) r on 0 = 0
        where
          ( r.timestamp is null
            or w.timestamp < r.timestamp
            or (w.timestamp = r.timestamp and w.sequence <= r.sequence)    
          )
          and (
            w.timestamp > wb.timestamp
            or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
          )
      ) a
      where a.r = 1) w_gb on True
  ),
  res as (
    select 
      discover_log.*,
      extract ('EPOCH' from discover_log.mf_end - discover_log.mf_start) as mf_runtime
    from discover_log
  )
select * 
from res
