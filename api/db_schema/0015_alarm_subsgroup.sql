/* 
drop table alarm_subsgroup;
*/

create table alarm_subsgroup (
  "user" varchar(200) not null,
  "group" varchar(200) not null,
  primary key ("user", "group")
)

GRANT ALL ON TABLE alarm_subsgroup TO aaa;
GRANT ALL ON TABLE alarm_subsgroup TO postgres;

