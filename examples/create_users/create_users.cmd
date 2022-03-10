@echo off

call i4c user set ^
  --input-data @users.txt ^
  --input-format txt.header.rows ^
  --input-foreach $[*] ^
  --$id $.id ^
  --input-placement $.name=$.nev ^
  --input-placement $.email=$.email ^
  --input-placement $.login_name=$.email ^
  --input-placement $.roles[0]=$.role ^
  --output-expr $[*] ^
  --output-template "{{id}} '{{name}}' {{status}} lin:{{login_name}} to:{{email}} {{roles}}{{nl}}"

