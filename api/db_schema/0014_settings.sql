/* 
drop table "settings";
*/

create table "settings" (
    key character varying (200) not null primary key,
    value text null
);

GRANT ALL ON TABLE public."settings" TO aaa;
GRANT ALL ON TABLE public."settings" TO postgres;

alter table "settings"
add column "public" boolean NOT NULL default false;

/*
truncate table "settings" cascade;
insert into "settings" values ('push_priv_key', '1234', false);
insert into "settings" values ('push_public_key', 'public1234', true);
insert into "settings" values ('push_email', 'email@sample.hu', true);
*/
