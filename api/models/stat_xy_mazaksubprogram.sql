with
  p as (select
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  p_begin as (
    select l.device, l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device in ('lathe', 'mill')
      and l.data_id = 'exec'
      and l.value_text = 'ACTIVE'
  ), 
  p_end as (
    select l.device, l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device in ('lathe', 'mill')
      and l.data_id = 'exec'
      and l.value_text != 'ACTIVE'
  ),
  p_pgm as (
    select l.device, l.value_text as "program", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device in ('lathe', 'mill')
      and l.data_id='pgm'
  ),
  p_spgm as (
    select l.device, l.value_text as "subprogram", l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device in ('lathe', 'mill')
      and l.data_id='spgm'
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
                 ) mpv on mpv.savepath = 'robot\\'||r."program"   /* todo: use proper path */
                          and mpv.r = 1
  ),
  workpiece_gb as (
    select l.value_text as gb, l.timestamp, l.sequence
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device='gom'
      and l.data_id='eval'
  ),
  discover_log as (
    select 
      wb.timestamp as mf_start,
      least(spgm_next.timestamp, we.timestamp) as mf_end,
      wb.device as mf_device,
      w_pgm."program" as mf_program,
      wb."subprogram" as mf_subprogram,
      w_project."project" as mf_project,
      w_project."version" as "mf_project version",
      w_gb.gb as "mf_workpiece good/bad"
    from p_spgm wb
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from p_begin as w
        where
          w.timestamp < wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence <= wb.sequence)    
      ) a
      where a.r = 1) w_exec_begin on w_exec_begin.device = wb.device
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from p_spgm as w
        where
          w.timestamp > wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence >= wb.sequence)    
      ) a
      where a.r = 1) spgm_next on spgm_next.device = wb.device    
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
      where a.r = 1) we on we.device = wb.device
    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from p_pgm as w
        where
          w.timestamp < wb.timestamp
          or (w.timestamp = wb.timestamp and w.sequence <= wb.sequence)    
      ) a
      where a.r = 1) w_pgm on w_pgm.device = wb.device
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
      where a.r = 1) w_project on 0=0
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
      where a.r = 1) w_gb on 0 = 0
  ),
  res as (
    select 
      discover_log.*,
      extract ('EPOCH' from discover_log.mf_end - discover_log.mf_start) as mf_runtime
    from discover_log
  )
select * 
from res
