@echo off

set alarm=highload_mill_A7080_1

del marker 2> nul
call i4c alarm subsgroups --group machinist --output-expr $[*] --output-file marker
if not exist marker (
  echo CREATING SUBSCRIPTION GROUP
  call i4c alarm subsgroup-set --name machinist --body "{\"users\":[]}" --output-file nul
)
del marker

echo CREATING/UPDATING ALARM
call i4c alarm set --name %alarm% --body @highload_mill_A7080_1.json --output-template "id: {{id}}"