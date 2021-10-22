insert into role values ('user_read', 'active');
insert into role values ('user_write', 'active');
insert into role values ('role_read', 'active');
insert into role values ('role_write', 'active');
insert into role values ('auth_read', 'active');
insert into role values ('auth_write', 'active');
insert into role values ('log_read', 'active');
insert into role values ('log_write', 'active');
insert into role values ('all_read', 'active');
insert into role values ('all_write', 'active');

insert into role_grant values ('user_read', 'get/users/{id}', array[]::varchar[]);
insert into role_grant values ('user_read', 'get/users', array[]::varchar[]);
insert into role_grant values ('user_write', 'put/users/{id}', array[]::varchar[]);
insert into role_grant values ('user_write', 'patch/users/{id}', array[]::varchar[]);
insert into role_grant values ('role_read', 'get/roles/{id}', array[]::varchar[]);
insert into role_grant values ('role_read', 'get/roles', array[]::varchar[]);
insert into role_grant values ('role_write', 'put/roles/{id}', array[]::varchar[]);
insert into role_grant values ('log_read', 'get/log/snapshot', array[]::varchar[]);
insert into role_grant values ('log_read', 'get/log/find', array[]::varchar[]);
insert into role_grant values ('log_read', 'get/log/meta', array[]::varchar[]);
insert into role_grant values ('log_write', 'post/log', array[]::varchar[]);

insert into role_subrole values ('user_write', 'user_read');
insert into role_subrole values ('role_write', 'role_read');
insert into role_subrole values ('auth_read', 'role_read');
insert into role_subrole values ('auth_read', 'user_read');
insert into role_subrole values ('auth_write', 'role_write');
insert into role_subrole values ('auth_write', 'user_write');
insert into role_subrole values ('auth_write', 'auth_read');
insert into role_subrole values ('all_read', 'auth_read');
insert into role_subrole values ('all_read', 'log_read');
insert into role_subrole values ('all_write', 'auth_write');
insert into role_subrole values ('all_write', 'log_write');
insert into role_subrole values ('all_write', 'all_read');

-- '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9' is for password 'titok'
insert into "user" values ('joe', 'joe', 'active', 'joe', '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9');
insert into "user" values ('jake', 'jake', 'active', 'jake', '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9');
insert into "user" values ('jason', 'jason', 'active', 'jason', '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9');
insert into "user" values ('james', 'james', 'active', 'james', '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9');
insert into "user" values ('jack', 'jack', 'active', 'jack', '/uOlIfQ4rm9yY/8CzZWaFWtxd+xuDTa/2wd0GEzic5VTxLF9');

insert into "user_role" values ('joe', 'auth_read');
insert into "user_role" values ('jason', 'all_write');
