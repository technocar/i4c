ALTER TABLE public.meta ALTER COLUMN name DROP NOT NULL;

update public.meta
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