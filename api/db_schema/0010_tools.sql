/* 
drop table "tools";
*/

create table "tools" (
    id character varying (200) not null primary key,
    "type" character varying (200) null
);
GRANT ALL ON TABLE "tools" TO aaa;
GRANT ALL ON TABLE "tools" TO postgres;
