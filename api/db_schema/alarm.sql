/* 
drop table "alarm_cond";
drop table "alarm";
*/

create table "alarm" (
    id SERIAL PRIMARY KEY,
    name character varying (200) null constraint uq_alarm_name unique,
    max_freq double precision null,
    last_check timestamp with time zone not NULL,
    last_report timestamp with time zone NULL
); 

GRANT ALL ON TABLE public."alarm" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_id_seq TO aaa;
GRANT ALL ON TABLE public."alarm" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_id_seq TO postgres;

create table "alarm_cond" (
    id SERIAL PRIMARY KEY,
    alarm integer not null constraint fk_pv references "alarm",
    log_row_category character varying (200) not null,
   
    device character varying (200) not null,
    data_id character varying (200) not null,
    aggregate_period double precision null,
    aggregate_count integer null,
    aggregate_method character varying (200) null,
    rel character varying (200) null,
    value_num double precision null,
    value_text character varying (200) null,
    age_min double precision null,
    age_max double precision null
); 

GRANT ALL ON TABLE public."alarm_cond" TO aaa;
GRANT USAGE, SELECT ON SEQUENCE alarm_cond_id_seq TO aaa;
GRANT ALL ON TABLE public."alarm_cond" TO postgres;
GRANT USAGE, SELECT ON SEQUENCE alarm_cond_id_seq TO postgres;
