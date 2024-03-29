-- delete from role_grant;

insert into role_grant values ('aaa', 'get/log/snapshot', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/log/find', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/log/meta', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/log', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/log/last_instance', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/login', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/projects', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/projects/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/projects', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/projects/{name}', array[]::varchar[]);

insert into role_grant values ('aaa', 'post/installations/{project}/{version}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/installations', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/installations/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/installations/{id}/{savepath:path}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/projects/{name}/v/{ver}', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/projects/{name}/v', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/projects/{name}/v/{ver}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/intfiles', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('aaa', 'delete/intfiles/v/{ver}/{path:path}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/files', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/workpiece', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/workpiece/{id}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/tools', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/tools/list_usage', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/tools', array[]::varchar[]);
insert into role_grant values ('aaa', 'delete/tools', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/tools/{tool_id}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/batch', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/batch/{id}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/defs', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/subs', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/subs/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/alarm/subs', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/alarm/subs/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/alarm/events/check', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/events', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/events/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/recips', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/subsgroupusage', array['any user']::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/alarm/subsgroups', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'delete/alarm/subsgroups/{name}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/stat/def', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/stat/def', array[]::varchar[]);
insert into role_grant values ('aaa', 'delete/stat/def/{id}', array['delete any']::varchar[]);
insert into role_grant values ('aaa', 'patch/stat/def/{id}', array['patch any']::varchar[]);
insert into role_grant values ('aaa', 'get/stat/data/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/stat/objmeta', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/privs', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/roles', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/roles/{name}', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/roles/{name}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/users', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/users/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/users/{id}', array[]::varchar[]);
insert into role_grant values ('aaa', 'patch/users/{id}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/pwdreset', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/pwdreset/sent', array[]::varchar[]);
insert into role_grant values ('aaa', 'post/pwdreset/fail', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/settings/{key}', array[]::varchar[]);
insert into role_grant values ('aaa', 'put/settings/{key}', array[]::varchar[]);

insert into role_grant values ('aaa', 'get/audit', array[]::varchar[]);
insert into role_grant values ('aaa', 'get/customers', array[]::varchar[]);