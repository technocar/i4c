alter table alarm
add column status character varying(200) COLLATE pg_catalog."default" NULL;

update alarm
set "status" = 'active';

alter table alarm
alter column status set not null;