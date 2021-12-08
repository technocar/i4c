with
  p as (select
          coalesce($1::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after
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
  )
select distinct mpv."project", mpv.version
from robot_program r
join lateral (select 
                m.*,
                rank() over (order by m.timestamp desc) r
              from map_project_version m
              where 
                m.timestamp <= r.timestamp
             ) mpv on mpv.savepath = 'robot/'||r."program"   /* todo: use proper path */
                      and mpv.r = 1
