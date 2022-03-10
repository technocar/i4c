@echo off

call i4c project new --body "{\"name\":\"A7080\"}
if errorlevel 1 (
  echo FAILED to create new project
  goto :eof
)

call i4c project ver-new --name A7080 --body @files.txt
if errorlevel 1 (
  echo FAILED to create project version
  goto :eof
)

