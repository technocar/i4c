delete from  public.meta
where data_id = 'connect';

delete from  public.log
where data_id = 'connect';

insert into public.meta (device, data_id, name, category, "type") values ('lathe', 'connect', 'connect', 'CONDITION', 'CONDITION');
insert into public.meta (device, data_id, name, category, "type") values ('mill', 'connect', 'connect', 'CONDITION', 'CONDITION');

insert into public.log (device, instance, timestamp, sequence, "data_id", value_text)
select
  a.device, 
  a.instance,
  a.timestamp - (interval '1 second'),
  0 as sequence,
  'connect' as "data_id",
  'Normal' as value_text
from (
  select 
    device, 
    instance,
    timestamp, 
    rank() over (partition by device, instance order by timestamp, sequence) "#r"
  from public.log
) a
where a."#r" = 1
