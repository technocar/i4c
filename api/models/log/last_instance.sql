select l.instance, l.sequence 
from public.log l 
where 
  l.instance is not null
  and l.device = $1
order by l.timestamp desc, l.sequence desc
limit 1