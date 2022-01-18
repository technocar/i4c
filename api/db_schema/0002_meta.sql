-- Table: meta

-- DROP TABLE meta;

CREATE TABLE IF NOT EXISTS meta
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
    CONSTRAINT meta_pkey PRIMARY KEY (device, data_id)
)

TABLESPACE pg_default;

ALTER TABLE meta
    OWNER to postgres;

GRANT ALL ON TABLE meta TO aaa;

GRANT ALL ON TABLE meta TO postgres;