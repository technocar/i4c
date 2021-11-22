/* 
drop table "alarm_recipient";
drop table "alarm_event";
drop table "alarm_sub";
drop table "alarm_cond";
drop table "alarm";
*/

create table "alarm" (
    id SERIAL PRIMARY KEY,
    name character varying (200) null constraint uq_alarm_name unique,
    "window" double precision null, 
    max_freq double precision null,
    last_check timestamp with time zone not NULL,
    last_report timestamp with time zone NULL,
    subsgroup character varying (200) not null
); 

GRANT ALL ON TABLE public."alarm" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_id_seq TO aaa;
GRANT ALL ON TABLE public."alarm" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_id_seq TO postgres;

create table "alarm_cond" (
    id SERIAL PRIMARY KEY,
    alarm integer not null constraint fk_pv references "alarm",
    log_row_category character varying (200) not null,
   
    device character varying (200) not null,
    data_id character varying (200) not null,
    aggregate_period double precision null,
    aggregate_count integer null,
    aggregate_method character varying (200) null,
    rel character varying (200) null,
    value_num double precision null,
    value_text character varying (200) null,
    age_min double precision null,
    age_max double precision null
); 

GRANT ALL ON TABLE public."alarm_cond" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_cond_id_seq TO aaa;
GRANT ALL ON TABLE public."alarm_cond" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_cond_id_seq TO postgres;


create table "alarm_sub" (
    id SERIAL PRIMARY KEY,
    groups character varying (200)[] not null,
    "user" character varying (200) null constraint fk_alarm_sub_user references "user", 
    method character varying (200) not null,
    address character varying (200) null,
    status character varying (200) not null
);

GRANT ALL ON TABLE "alarm_sub" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_sub_id_seq TO aaa;
GRANT ALL ON TABLE "alarm_sub" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_sub_id_seq TO postgres;


create table "alarm_event" (
    id SERIAL PRIMARY KEY,
    alarm integer not null constraint fk_alarm references "alarm",
    created timestamp with time zone NOT NULL,
    summary character varying (200) not null,
    description text NULL
);

GRANT ALL ON TABLE "alarm_event" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_event_id_seq TO aaa;
GRANT ALL ON TABLE "alarm_event" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_event_id_seq TO postgres;


create table "alarm_recipient" (
    id SERIAL PRIMARY KEY,
    event integer not null constraint fk_event references "alarm_event",
    "user" character varying (200) null constraint fk_alarm_sub_user references "user", 
    method character varying (200) not null,
    address character varying (200) null,
    status character varying (200) not null
);

GRANT ALL ON TABLE "alarm_recipient" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_recipient_id_seq TO aaa;
GRANT ALL ON TABLE "alarm_recipient" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_recipient_id_seq TO postgres;

/*
delete from "alarm_recipient";
delete from "alarm_event";
delete from "alarm_sub";
delete from "alarm_cond";
delete from "alarm";

insert into "alarm" values (5,'al1',200,10,'2021-11-16'::timestamp,null,'grp1');
insert into "alarm_cond" values (1,5,'EVENT','lathe','exec',null,null,null,'=',null,'ACTIVE',null,null);
insert into "alarm_cond" values (2,5,'EVENT','lathe','pgm' ,null,null,null,'=',null,'ALARMTEST',null,null);
insert into "alarm_cond" values (3,5,'SAMPLE','lathe','xl',2,null,'avg','>',100,null,null,null);
insert into "alarm_sub" values (1,Array['grp1','grp2'],'1','none',null,'active');
*/