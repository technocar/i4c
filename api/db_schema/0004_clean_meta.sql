ALTER TABLE meta ALTER COLUMN name DROP NOT NULL;

update meta
set 
  device = nullif(device,''),
  data_id = nullif(data_id,''),
  name = nullif(name,''),
  nice_name = nullif(nice_name,''),
  system1 = nullif(system1,''),
  system2 = nullif(system2,''),
  category = nullif(category,''),
  type = nullif(type,''),
  subtype = nullif(subtype,''),
  unit = nullif(unit,'');
  
insert into meta (device,data_id,name,category) values ('mill','install_tool','install_tool','EVENT')
insert into meta (device,data_id,name,category) values ('mill','remove_tool','install_tool','EVENT')
insert into meta (device,data_id,name,category) values ('lathe','install_tool','install_tool','EVENT')
insert into meta (device,data_id,name,category) values ('lathe','remove_tool','install_tool','EVENT')
