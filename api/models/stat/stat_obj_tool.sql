with
  p as (select
          coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
              as after
  ),
  p_tid as (
    select l.device, l.timestamp, l.sequence, l.value_text as slot_id
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.data_id = 'tid'
  ),
  p_installed as (
    select
      l.device,
      l.timestamp, 
      l.sequence,
      l.value_text "tool_id",
      l.value_extra "slot_id",
      t.type
    from log l
    cross join p
    left join tools t on t.id = l.value_text
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before  
      and l.data_id = 'install_tool'
  ),
  tool as (
    select 
      p_tid.*,
      last_installed."tool_id",
      last_installed."type",
      rank() over (partition by p_tid.device order by p_tid.timestamp, p_tid.sequence) r    
    from p_tid
    cross join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp desc, w.sequence desc) r
        from p_installed as w
        where
          w.device = p_tid.device
          and w.slot_id = p_tid.slot_id
          and ( w.timestamp < p_tid.timestamp
                or (w.timestamp = p_tid.timestamp and w.sequence < p_tid.sequence))
      ) a
      where a.r = 1
    ) last_installed
  ),
  p_active as (
    select l.device, l.timestamp, l.sequence, l.value_text
    from log l
    cross join p
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before
      and l.device in ('lathe', 'mill')
      and l.data_id = 'exec'
  ),
  p_begin as (
    select l.device, l.timestamp, l.sequence
    from p_active l
    where
      l.value_text = 'ACTIVE'
  ), 
  p_end as (
    select l.device, l.timestamp, l.sequence
    from p_active l
    where
      l.value_text != 'ACTIVE'
  ),
  tool_selected as (
    select 
      tu.*,
      tu.timestamp as start_timestamp,
      coalesce(tu_next.timestamp, least(coalesce(p.before, now()), now())) as end_timestamp
    from tool tu
    cross join p
    left join tool tu_next on tu_next.device = tu.device and tu_next.r = tu.r + 1
  ),
  tool_usage as (
    select 
      *,
      greatest(wp_begin.timestamp, ts.start_timestamp) as usage_start,
      least(wp_end.timestamp, ts.end_timestamp) as usage_end
    from tool_selected ts
    join lateral (
        select 
          w.timestamp
        from p_begin as w
        where
          w.device = ts.device
          and w.timestamp >= ts.start_timestamp
          and w.timestamp <= ts.end_timestamp

        union all

        select a.timestamp 
        from (
          select 
            w.*,
            rank() over (order by w.timestamp desc, w.sequence desc) r
          from p_end as w
          where
            w.device = ts.device
            and w.timestamp < ts.start_timestamp
        ) a
        where a.r = 1      
      ) wp_begin on True

    left join lateral (
      select * from (
        select 
          w.*,
          rank() over (order by w.timestamp asc, w.sequence asc) r
        from p_end as w
        where
          w.device = ts.device
          and w.timestamp > wp_begin.timestamp
          and w.timestamp <= ts.end_timestamp
      ) a
      where a.r = 1) wp_end on True
      
    where 
      wp_end.timestamp is null 
      or (wp_end.timestamp >= ts.start_timestamp)
  ),
  res as (
    select
      t.tool_id as "mf_id",
      min(t."type") as "mf_type",
      count(*) "mf_count used",
      sum(extract ('EPOCH' from t.usage_end - t.usage_start)) as "mf_accumulated cutting time"
    from tool_usage t
    group by t.tool_id
  )
select * 
from res