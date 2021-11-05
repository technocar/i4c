/* 
drop table "workpiece_note";
drop table "workpiece";
*/

create table "workpiece" (
    id SERIAL PRIMARY KEY,
    project character varying (200) not null constraint fk_project references "projects",
    batch character varying (200) null,
    status character varying (200) not null,
    log_window_begin timestamp with time zone NULL,
    log_window_end timestamp with time zone NULL
);
GRANT ALL ON TABLE public."workpiece" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE workpiece_id_seq TO aaa;
GRANT ALL ON TABLE public."workpiece" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE workpiece_id_seq TO postgres;


create table "workpiece_note" (
    id SERIAL PRIMARY KEY,
    workpiece int not null constraint fk_project references "workpiece",
    "user" character varying (200) not null constraint fk_userrole_user references "user", 
    "timestamp" timestamp with time zone NOT NULL,
    "text" text NOT NULL,
    deleted boolean NOT NULL default false
);

GRANT ALL ON TABLE public."workpiece_note" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE workpiece_note_id_seq TO aaa;
GRANT ALL ON TABLE public."workpiece_note" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE workpiece_note_id_seq TO postgres;

/*
delete from "workpiece_note";
delete from "workpiece";
insert into "workpiece" values (1,'proj1',null,'good','2018-08-22'::timestamp,'2021-08-22'::timestamp);
insert into "workpiece_note" values (1,1,'1','2021-11-04'::timestamp,'hello',false);
insert into "workpiece_note" values (2,1,'1','2021-11-05'::timestamp,'bello',false);
insert into "workpiece" values (2,'proj1','1','bad','2018-08-22'::timestamp,'2021-08-22'::timestamp);
insert into "workpiece" values (3,'proj1','1','bad','2018-08-22'::timestamp,'2021-08-22'::timestamp);
insert into "workpiece" values (4,'proj48','3','good','2018-08-22'::timestamp,'2021-08-22'::timestamp);
insert into "workpiece" values (5,'proj48','4','bad','2018-08-22'::timestamp,'2021-08-22'::timestamp);
*/