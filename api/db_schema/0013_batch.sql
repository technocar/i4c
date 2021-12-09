/* 
drop table "batch";
*/

create table "batch" (
    id character varying (200) not null primary key,
    client character varying (200) null,
    project character varying (200) not null constraint fk_project references "projects",
    target_count int null,
    status character varying (200) not null
);

GRANT ALL ON TABLE public."batch" TO aaa;
GRANT ALL ON TABLE public."batch" TO postgres;

/*

with 
  b as (
    select distinct 
      w.batch 
    from workpiece w
    left join batch b on b.id = w.batch
    where 
      b.id is null
      and w.batch is not null
  )
insert into batch (id, project, status)
select 
  b.batch, 
  'A7080',
  'active'
from b;

*/