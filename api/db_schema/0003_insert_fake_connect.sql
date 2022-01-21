delete from  meta
where data_id = 'connect';

delete from  log
where data_id = 'connect';

insert into meta (device, data_id, name, category, "type") values ('lathe', 'connect', 'connect', 'CONDITION', 'CONDITION');
insert into meta (device, data_id, name, category, "type") values ('mill', 'connect', 'connect', 'CONDITION', 'CONDITION');

insert into log (device, instance, timestamp, sequence, "data_id", value_text)
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
  from log
) a
where a."#r" = 1
