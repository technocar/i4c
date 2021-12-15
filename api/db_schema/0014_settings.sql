/* 
drop table "settings";
*/

create table "settings" (
    key character varying (200) not null primary key,
    value character varying (200) null
);

GRANT ALL ON TABLE public."settings" TO aaa;
GRANT ALL ON TABLE public."settings" TO postgres;

/*
truncate table "settings" cascade;
insert into "settings" values ('push_priv_key', null);
insert into "settings" values ('push_public_key', null);
*/
