alter table stat_timeseries
add column agg_sep_value character varying(200) COLLATE pg_catalog."default" NULL,
add column agg_sep_value_extra character varying(200) COLLATE pg_catalog."default" NULL,
add column series_sep_value character varying(200) COLLATE pg_catalog."default" NULL,
add column series_sep_value_extra character varying(200) COLLATE pg_catalog."default" NULL;
