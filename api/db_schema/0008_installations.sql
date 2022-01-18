/* 
drop table "installation_file";
drop table "installation";
 
*/

create table "installation" (
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone NOT NULL,
    project character varying (200) not null constraint fk_project references "projects",
    invoked_version character varying (200) not null,
    real_version int not null,
    status character varying (200) not null,
    status_msg character varying (200) null
);
GRANT ALL ON TABLE "installation" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE installation_id_seq TO aaa;
GRANT ALL ON TABLE "installation" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE installation_id_seq TO postgres;

create table "installation_file" (
    id SERIAL PRIMARY KEY,
    installation integer not null constraint fk_project references "installation",
    savepath character varying (2000) not null
);

GRANT ALL ON TABLE "installation_file" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE installation_file_id_seq TO aaa;
GRANT ALL ON TABLE "installation_file" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE installation_file_id_seq TO postgres;
