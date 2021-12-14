create table "user" (
    id character varying (200) not null primary key,
    name character varying (200) not null,
    status character varying (200) not null,
    login_name character varying (200) null constraint uq_user_login unique,
    password_verifier character varying (200) null,
    public_key character varying (200) null
);

alter table "user"
add column pwd_reset_token VARCHAR(200) null;

alter table "user"
add column customer VARCHAR(200) null;

create table "role" (
    name character varying (200) not null primary key,
    status character varying (200) not null
);

create table "user_role" (
    "user" character varying (200) not null constraint fk_userrole_user references "user",
    "role" character varying (200) not null constraint fk_userrole_role references "role",
    primary key ("user", "role")
);

create table "role_subrole" (
    "role" character varying (200) not null constraint fk_rolesub_role references "role",
    "subrole" character varying (200) not null constraint fk_rolesub_sub references "role",
    primary key ("role", "subrole")
);

create table "role_grant" (
    "role" character varying (200) not null constraint fk_rolegr_role references "role",
    "endpoint" character varying (500) not null,
    "features" character varying (200) [] not null,
    primary key ("role", "endpoint")
);

GRANT ALL ON TABLE public."user" TO aaa;
GRANT ALL ON TABLE public."user" TO postgres;

GRANT ALL ON TABLE public."role" TO aaa;
GRANT ALL ON TABLE public."role" TO postgres;

GRANT ALL ON TABLE public."user_role" TO aaa;
GRANT ALL ON TABLE public."user_role" TO postgres;

GRANT ALL ON TABLE public."role_subrole" TO aaa;
GRANT ALL ON TABLE public."role_subrole" TO postgres;

GRANT ALL ON TABLE public."role_grant" TO aaa;
GRANT ALL ON TABLE public."role_grant" TO postgres;

create or replace view test_user_grant as
with
  recursive deep_role_r as
    (select distinct "name" as toprole, "name" as midrole, "name" as subrole from "role"
     union
     select deep_role_r.toprole, role_subrole.role as midrole, role_subrole.subrole
     from deep_role_r join role_subrole on deep_role_r.subrole = role_subrole.role),
  deep_role as (select distinct toprole as role, subrole from deep_role_r)
select "user".id as user_id, role_grant.endpoint, role_grant.features
from "user"
join user_role on "user".id = user_role."user"
join deep_role on deep_role.role = user_role."role"
join role_grant on deep_role.subrole = role_grant."role"


/*

with
  recursive deep_role_r as
    (select distinct "name" as toprole, "name" as midrole, "name" as subrole from "role"
     union
     select deep_role_r.toprole, role_subrole.role as midrole, role_subrole.subrole
     from deep_role_r 
     join role_subrole on deep_role_r."subrole" = role_subrole."role"),
  deep_role as (select distinct toprole as role, subrole from deep_role_r)
select role_grant.features, "user".id, "user".status, "user".password_verifier, "user".public_key
from "user"
left join ( user_role 
            join deep_role on deep_role.role = user_role."role"
            join role_grant on deep_role.subrole = role_grant."role"
          ) on "user".id = user_role."user"
where "user".login_name = $1
and role_grant.endpoint = $2

*/