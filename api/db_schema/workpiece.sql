/* 
drop table "workpiece_note";
drop table "workpiece";
*/

create table "workpiece" (
    id character varying (200) not null primary key,
    batch character varying (200) null,
    manual_status character varying (200) null
);
GRANT ALL ON TABLE public."workpiece" TO aaa;
GRANT ALL ON TABLE public."workpiece" TO postgres;


create table "workpiece_note" (
    id SERIAL PRIMARY KEY,
    workpiece character varying (200) not null,
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
insert into "workpiece" values ('sdfsdf',null,'good');
insert into "workpiece_note" values (1,'sdfsdf','1','2021-11-04'::timestamp,'hello',false);
insert into "workpiece_note" values (2,'sdfsdf','1','2021-11-05'::timestamp,'bello',false);
insert into "workpiece" values ('dfsf',null,'bad');
insert into "workpiece_note" values (3,'32423432','1','2021-11-05'::timestamp,'bello',false);
*/