-- Table: public.minimon_log

-- DROP TABLE public.minimon_log;

CREATE TABLE IF NOT EXISTS public.minimon_log
(
    device character varying(200) COLLATE pg_catalog."default" NOT NULL,
    instance character varying(200) COLLATE pg_catalog."default",
    "timestamp" timestamp with time zone NOT NULL,
    sequence integer NOT NULL,
    data_id character varying(200) COLLATE pg_catalog."default" NOT NULL,
    value_num double precision,
    value_text character varying(200) COLLATE pg_catalog."default",
    value_extra character varying(200) COLLATE pg_catalog."default",
    value_aux json
)

TABLESPACE pg_default;

ALTER TABLE public.minimon_log
    OWNER to postgres;

GRANT ALL ON TABLE public.minimon_log TO aaa;

GRANT ALL ON TABLE public.minimon_log TO postgres;

COMMENT ON COLUMN public.minimon_log.device
    IS 'Mill, Lathe';
-- Index: idx_ts

-- DROP INDEX public.idx_ts;

CREATE UNIQUE INDEX idx_ts
    ON public.minimon_log USING btree
    (device COLLATE pg_catalog."default" ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;
    
CREATE INDEX idx_dts
    ON public.minimon_log USING btree
    (device COLLATE pg_catalog."default" ASC NULLS LAST, data_id COLLATE pg_catalog."default" ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;