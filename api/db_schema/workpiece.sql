/* 
drop table "workpiece_note";
drop table "workpiece";
*/

create table "workpiece" (
    id SERIAL PRIMARY KEY,
    project character varying (200) not null constraint fk_project references "projects",
    batch character varying (200) null,
    status character varying (200) not null
);
GRANT ALL ON TABLE public."workpiece" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE workpiece_id_seq TO aaa;
GRANT ALL ON TABLE public."workpiece" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE workpiece_id_seq TO postgres;


create table "workpiece_note" (
    id SERIAL PRIMARY KEY,
    "user" character varying (200) not null constraint fk_userrole_user references "user", 
    "timestamp" timestamp with time zone NOT NULL,
    "text" text NOT NULL,
    deleted boolean NOT NULL default false
);

GRANT ALL ON TABLE public."workpiece_note" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE workpiece_note_id_seq TO aaa;
GRANT ALL ON TABLE public."workpiece_note" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE workpiece_note_id_seq TO postgres;
