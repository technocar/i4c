/* 
drop table "project_file";
drop table "file_int";
drop table "file_unc";
drop table "file_git";
drop table "project_label";
drop table "project_version";
drop table "projects";
 
*/

create table "projects" (
    name character varying (200) not null primary key,
    status character varying (200) not null,
    extra json null
);

GRANT ALL ON TABLE public."projects" TO aaa;
GRANT ALL ON TABLE public."projects" TO postgres;

create table "project_version" (
    id SERIAL PRIMARY KEY,
    project character varying (200) not null constraint fk_project references "projects",
    ver integer not null,
    status character varying (200) not null
);

CREATE UNIQUE INDEX idx_project_ver ON "project_version" (project, ver);

GRANT ALL ON TABLE public."project_version" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE project_version_id_seq TO aaa;
GRANT ALL ON TABLE public."project_version" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE project_version_id_seq TO postgres;

create table "project_label" (
    project_ver integer not null constraint fk_pv references "project_version",
    label character varying (200) null
);

GRANT ALL ON TABLE public."project_label" TO aaa;
GRANT ALL ON TABLE public."project_label" TO postgres;



create table "file_git" (
    id SERIAL PRIMARY KEY,
    repo character varying (200) not null,
    name character varying (200) not null,
    commit character varying (200) not null
);
GRANT ALL ON TABLE public."file_git" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE file_git_id_seq TO aaa;
GRANT ALL ON TABLE public."file_git" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE file_git_id_seq TO postgres;

create table "file_unc" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null
);
GRANT ALL ON TABLE public."file_unc" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE file_unc_id_seq TO aaa;
GRANT ALL ON TABLE public."file_unc" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE file_unc_id_seq TO postgres;

create table "file_int" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    ver integer,
    content_hash character varying (200) not null,
    content bytea not null
);
CREATE UNIQUE INDEX idx_file_int_name_ver ON "file_int" (name, ver);
GRANT ALL ON TABLE public."file_int" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE file_int_id_seq TO aaa;
GRANT ALL ON TABLE public."file_int" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE file_int_id_seq TO postgres;

create table "project_file" (
    project_ver integer not null constraint pv references "project_version",
    savepath character varying (2000) not null,
    file_git integer null constraint fk_git references "file_git", 
    file_unc integer null constraint fk_unc references "file_unc",  
    file_int integer null constraint fk_int references "file_int",
    primary key (project_ver, savepath)
);

GRANT ALL ON TABLE public."project_file" TO aaa;
GRANT ALL ON TABLE public."project_file" TO postgres;

/* 
truncate table "projects", "project_version", "project_label", "project_file" cascade;
insert into "projects" (name, status) values ('proj1','active');
insert into "project_version" (id, project, ver, status) values (12, 'proj1', 1, 'final');
insert into "project_label" (project_ver, label) values (12, 'label1');
insert into "project_file" (project_ver, savepath) values (12, 'file1');
insert into "project_file" (project_ver, savepath) values (12, 'file2');
 
*/
