with 
  params as (
    select 
      $1::timestamp with time zone -- */ '2021-08-26 05:40:33.212000+00:00'::timestamp with time zone
        as ts  
  ),
  actv as (
    select * from (
      select
        l.device, l.timestamp, l."sequence"
      from public.log l
      cross join params p
      where 
         l.timestamp <= p.ts
         and l.data_id = 'exec'
         and l.value_text = 'ACTIVE' 
         and l.device in ('mill', 'lathe')
      order by l.timestamp desc, l."sequence" desc
      limit 1
    )a

    union all

    select * from (
      select
        l.device, l.timestamp, l."sequence"
      from public.meta m
      cross join params p
      join public.log l 
          on l.device = m.device
             and l.data_id = m.data_id
      where 
        l.timestamp <= p.ts
        and l.device in ('robot', 'gom')
        and m.category = 'EVENT'
      order by l.timestamp desc, l."sequence" desc
      limit 1
    )a

    union all

    select * from (
      select
        'gom' as device, l.timestamp, l."sequence"
      from public.log l
      cross join params p
      where 
         l.timestamp <= p.ts
         and l.data_id = 'gom'
         and l.value_text = 'STARTED' 
         and l.device = 'robot'
      order by l.timestamp desc, l."sequence" desc
      limit 1
    )a
  )
select *
from actv
order by actv.timestamp desc, actv."sequence" desc
limit 1