-- Table: public.minimon_meta

-- DROP TABLE public.minimon_meta;

CREATE TABLE IF NOT EXISTS public.minimon_meta
(
    device character varying(200) COLLATE pg_catalog."default" NOT NULL,
    data_id character varying(200) COLLATE pg_catalog."default" NOT NULL,
    name character varying(200) COLLATE pg_catalog."default" NULL,
    nice_name character varying(200) COLLATE pg_catalog."default",
    system1 character varying(200) COLLATE pg_catalog."default",
    system2 character varying(200) COLLATE pg_catalog."default",
    category character varying(200) COLLATE pg_catalog."default",
    type character varying(200) COLLATE pg_catalog."default",
    subtype character varying(200) COLLATE pg_catalog."default",
    unit character varying(200) COLLATE pg_catalog."default",
    CONSTRAINT minimon_meta_pkey PRIMARY KEY (device, data_id)
)

TABLESPACE pg_default;

ALTER TABLE public.minimon_meta
    OWNER to postgres;

GRANT ALL ON TABLE public.minimon_meta TO aaa;

GRANT ALL ON TABLE public.minimon_meta TO postgres;