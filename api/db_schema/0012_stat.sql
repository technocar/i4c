/* 
drop table "stat_timeseries_filter";
drop table "stat_timeseries";
drop table "stat";
*/

create table "stat" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    "user" character varying (200) not null constraint fk_stat_timeseries_filter_user references "user", 
    shared boolean NOT NULL default false,
    modified timestamp with time zone not NULL
); 

CREATE UNIQUE INDEX idx_name_user ON "stat" (name, "user");

GRANT ALL ON TABLE public."stat" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE stat_id_seq TO aaa;
GRANT ALL ON TABLE public."stat" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE stat_id_seq TO postgres;

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

/*
delete from "stat_timeseries_filter";
delete from "stat_timeseries";
delete from "stat";

insert into "stat" values (-1, 'stat1', '1', false , now());
insert into "stat_timeseries" values (-1, null, null, 'P1M'::interval, 'lathe', 'sl', null, null, null, null, null, null, 'timestamp');
insert into "stat_timeseries_filter" values (-1, -1, 'lathe', 'pgm', '*', 'a', null, null);
*/