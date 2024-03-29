-- Table: log

-- DROP TABLE log;

CREATE TABLE IF NOT EXISTS log
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

ALTER TABLE log
    OWNER to postgres;

GRANT ALL ON TABLE log TO aaa;

GRANT ALL ON TABLE log TO postgres;

COMMENT ON COLUMN log.device
    IS 'Mill, Lathe';
-- Index: idx_ts

-- DROP INDEX idx_ts;

CREATE UNIQUE INDEX idx_ts
    ON log USING btree
    (device COLLATE pg_catalog."default" ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;
    
CREATE INDEX idx_dts
    ON log USING btree
    (device COLLATE pg_catalog."default" ASC NULLS LAST, data_id COLLATE pg_catalog."default" ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;

CREATE UNIQUE INDEX idx_ts_wo_device
    ON log USING btree
    ("timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;
    
CREATE INDEX idx_dts_wo_device
    ON log USING btree
    (data_id COLLATE pg_catalog."default" ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST)
    TABLESPACE pg_default;