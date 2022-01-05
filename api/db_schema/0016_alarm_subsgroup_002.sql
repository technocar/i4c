ALTER TABLE alarm_subsgroup
RENAME TO alarm_subsgroup_map;

create table alarm_subsgroup (
  "group" varchar(200) not null,
  primary key ("group")
);

GRANT ALL ON TABLE public.alarm_subsgroup TO aaa;
GRANT ALL ON TABLE public.alarm_subsgroup TO postgres;

insert into alarm_subsgroup ("group")
select distinct "group" from alarm_subsgroup_map;

ALTER TABLE alarm_subsgroup_map 
ADD CONSTRAINT fk_alarm_subsgroup_map__alarm_subsgroup
FOREIGN KEY ("group") 
REFERENCES alarm_subsgroup ("group");

ALTER TABLE alarm_subsgroup_map 
ADD CONSTRAINT fk_alarm_subsgroup_map__user
FOREIGN KEY ("user") 
REFERENCES "user" ("id");

ALTER TABLE alarm 
ADD CONSTRAINT fk_alarm__alarm_subsgroup
FOREIGN KEY ("subsgroup") 
REFERENCES alarm_subsgroup ("group");
