create table "user" (
    id character varying (200) not null primary key,
    name character varying (200) not null,
    status character varying (200) not null,
    password_verifier character varying (200) null,
    public_key character varying (200) null
);

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


create or replace view test_user_grant as
with
  recursive deep_role_r as
    (select distinct role as toprole, role as midrole, role as subrole from role_subrole
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
    (select distinct role as toprole, role as midrole, role as subrole from role_subrole
     union
     select deep_role_r.toprole, role_subrole.role as midrole, role_subrole.subrole
     from deep_role_r join role_subrole on deep_role_r.subrole = role_subrole.role),
  deep_role as (select distinct toprole as role, subrole from deep_role_r)
select role_grant.features, "user".status, "user".password_verifier, "user".public_key
from "user"
join user_role on "user".id = user_role."user"
join deep_role on deep_role.role = user_role."role"
join role_grant on deep_role.subrole = role_grant."role"
where "user".id = $1
and role_grant.endpoint = $2

*/