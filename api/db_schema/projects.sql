create table "projects" (
    name character varying (200) not null primary key,
    status character varying (200) not null,
    extra json null,
    created_at timestamp with time zone NOT NULL,
    created_by character varying (200) not null constraint fk_user references "user"
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
GRANT ALL ON TABLE public."project_version" TO postgres;

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
GRANT ALL ON TABLE public."file_git" TO postgres;

create table "file_unc" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null
);
GRANT ALL ON TABLE public."file_unc" TO aaa;
GRANT ALL ON TABLE public."file_unc" TO postgres;

create table "file_int_content" (
    content_hash character varying (200) not null primary key,
    file_data BYTEA not null
);
GRANT ALL ON TABLE public."file_int_content" TO aaa;
GRANT ALL ON TABLE public."file_int_content" TO postgres;

create table "file_int" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    ver integer,
    content_hash character varying (200) not null constraint fk_content references "file_int_content"
);
GRANT ALL ON TABLE public."file_int" TO aaa;
GRANT ALL ON TABLE public."file_int" TO postgres;

create table "project_file" (
    project_ver integer not null constraint pv references "project_version",
    savepath character varying (200) not null,
    file_git integer null constraint fk_git references "file_git", 
    file_unc integer null constraint fk_unc references "file_unc",  
    file_int integer null constraint fk_int references "file_int"
);

GRANT ALL ON TABLE public."project_file" TO aaa;
GRANT ALL ON TABLE public."project_file" TO postgres;
