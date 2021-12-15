/* 
drop table "stat_xy_filter";
drop table "stat_xy_other";
drop table "stat_xy_object_params";
drop table "stat_xy";
drop table "stat_timeseries_filter";
drop table "stat_timeseries";
drop table "stat_visual_setting";
drop table "stat";
*/

create table "stat" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    "user" character varying (200) not null constraint fk_stat_timeseries_filter_user references "user", 
    shared boolean NOT NULL default false,
    modified timestamp with time zone not NULL
); 

alter table "stat"
add column customer VARCHAR(200) null;

CREATE UNIQUE INDEX idx_name_user ON "stat" (name, "user");

GRANT ALL ON TABLE public."stat" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_id_seq TO aaa;
GRANT ALL ON TABLE public."stat" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_id_seq TO postgres;

create table "stat_visual_setting" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    
    title character varying (200) null,
    subtitle character varying (200) null,
    
    xaxis_caption character varying (200) null,
    yaxis_caption character varying (200) null,
    
    legend_position character varying (200) null,
    legend_align character varying (200) null
); 


GRANT ALL ON TABLE public."stat_visual_setting" TO aaa;
GRANT ALL ON TABLE public."stat_visual_setting" TO postgres;


create table "stat_timeseries" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null,
    metric_device character varying (200) not null,
    metric_data_id character varying (200) not null,
    agg_func character varying (200) null,
    agg_sep_device character varying (200) null,
    agg_sep_data_id character varying (200) null,
    series_name character varying (200) null,
    series_sep_device character varying (200) null,
    series_sep_data_id character varying (200) null,
    xaxis character varying (200) not null
); 


GRANT ALL ON TABLE public."stat_timeseries" TO aaa;
GRANT ALL ON TABLE public."stat_timeseries" TO postgres;

create table "stat_timeseries_filter" (
    id SERIAL PRIMARY KEY,
    timeseries integer not null constraint fk_pv references "stat_timeseries" on delete cascade,
    
    device character varying (200) not null,
    data_id character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null,
    age_min double precision null,
    age_max double precision null    
);

GRANT ALL ON TABLE "stat_timeseries_filter" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_timeseries_filter_id_seq TO aaa;
GRANT ALL ON TABLE "stat_timeseries_filter" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_timeseries_filter_id_seq TO postgres;


create table "stat_xy" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    
    object_name character varying (200) not null,
    
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null,
    
    x_field character varying (200) not null,
    y_field character varying (200) null,
    shape character varying (200) null,
    color character varying (200) null
); 


GRANT ALL ON TABLE public."stat_xy" TO aaa;
GRANT ALL ON TABLE public."stat_xy" TO postgres;

create table "stat_xy_object_params" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    
    key character varying (200) not null,
    value character varying (200) null
);

GRANT ALL ON TABLE "stat_xy_object_params" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_object_params_id_seq TO aaa;
GRANT ALL ON TABLE "stat_xy_object_params" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_object_params_id_seq TO postgres;


create table "stat_xy_other" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    
    field_name character varying (200) not null
);

GRANT ALL ON TABLE "stat_xy_other" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_other_id_seq TO aaa;
GRANT ALL ON TABLE "stat_xy_other" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_other_id_seq TO postgres;


create table "stat_xy_filter" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    
    field_name character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null
);

GRANT ALL ON TABLE "stat_xy_filter" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_filter_id_seq TO aaa;
GRANT ALL ON TABLE "stat_xy_filter" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_filter_id_seq TO postgres;



/*
delete from "stat_xy_filter" where id<0;
delete from "stat_xy_other" where id<0;
delete from "stat_xy_object_params" where id<0;
delete from "stat_xy" where id<0;
delete from "stat_timeseries_filter" where id<0;
delete from "stat_timeseries" where id<0;
delete from "stat_visual_setting" where id<0;
delete from "stat" where id<0;

insert into "stat" values (-2, 'stat1', '1', false , now());
insert into "stat_timeseries" values (-2, null, null, 'P1M'::interval, 'lathe', 'sl', null, null, null, null, null, null, 'timestamp');
insert into "stat_timeseries_filter" values (-2, -2, 'lathe', 'pgm', '*', 'a', null, null);

insert into "stat" values (-3, 'stat-2', '1', false , now());
insert into "stat_xy" values (-3, 'mazakprogram', null, null, 'P1M'::interval, 'avg_x_load', 'avg_y_load', null, null); 


*/