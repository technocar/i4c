with
  p as (select 
     $1::varchar(200) -- */ 'lathe'
       as device,
     $2::varchar(200) -- */ 'cf'
       as data_id,
     $3::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
       as last_check,
     $4::timestamp with time zone -- */ '2021-08-24 07:56:00.957133+02'::timestamp with time zone
       as "now"
   ),
  before as (
    select
      l.timestamp,
      l.sequence,
      l.value_num,
      l.value_text
    from log l
    cross join p
    where 
      l.timestamp <= p.last_check
      and l.device = p.device
      and l.data_id = p.data_id
    order by l.timestamp desc, l."sequence" desc
    limit 1
  ),
  after as (
    select
      l.timestamp,
      l.sequence,
      l.value_num,
      l.value_text
    from log l
    cross join p
    where 
      l.timestamp > p.last_check
      and l.timestamp <= p."now"
      and l.device = p.device
      and l.data_id = p.data_id
  ),
  closing as (
    select
      now() as timestamp,
      0 as sequence,
      null::double precision as value_num,
      null::varchar(200) as value_text
  )
select * from before
union all
select * from after
union all
select * from closing

order by timestamp asc, "sequence" asc