with
  p as (select
          /* coalesce($1::timestamp with time zone,'2199-01-01'::timestamp with time zone) -- */ '2022-10-24 07:56:00.957133+02'::timestamp with time zone
              as before,
          /* coalesce($2::timestamp with time zone,'1899-01-01'::timestamp with time zone) -- */ '2021-10-24 07:56:00.957133+02'::timestamp with time zone
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
    from public.log l
    cross join p
    left join tools t on t.id = l.value_text
    where
      l.timestamp >= p.after
      and l.timestamp <= p.before  
      and l.data_id = 'install_tool'
  ),
  tool_usage as (
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
    select l.device, l.timestamp, l.sequence
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
    from p_active
    where
      l.value_text = 'ACTIVE'
  ), 
  p_end as (
    select l.device, l.timestamp, l.sequence
    from p_active
    where
      l.value_text != 'ACTIVE'
  ),
  tool_usage_ts as (
    select 
      tu.*,
      greatest(wp_begin.timestamp, tu.timestamp) as start_timestamp,
      coalesce(tu_next.timestamp, least(coalesce(p.before, now()), now())) as end_timestamp
    from tool_usage tu
    cross join p
    left join tool_usage tu_next on tu_next.device = tu.device and tu_next.r = tu.r + 1
    join lateral (
        select 
          w.timestamp
        from p_begin as w
        where
          w.device = tu.device
          and w.timestamp > tu.timestamp
          and (w.timestamp < tu_next.timestamp or tu_next.timestamp is null)

        union all

        select a.timestamp 
        from (
          select 
            w.*,
            rank() over (order by w.timestamp desc, w.sequence desc) r
          from p_end as w
          where
            w.device = tu.device
            and w.timestamp <= tu.timestamp
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
          w.device = tu.device
          and w.timestamp > tu.timestamp
          and (w.timestamp < tu_next.timestamp or tu_next.timestamp is null)
          and ( w.timestamp > wp_begin.timestamp
                or (w.timestamp = wp_begin.timestamp and w.sequence >= wp_begin.sequence)
               )
      ) a
      where a.r = 1) wp_end on True
  ),
  res as (
    select
      t.tool_id as "mf_tool_id",
      min(t."type") as "mf_type",
      count(*) "mf_count used",
      sum(extract ('EPOCH' from t.end_timestamp - t.start_timestamp)) as "mf_accumulated cutting time"
    from tool_usage_ts t
    group by t.tool_id
  )
select * 
from res