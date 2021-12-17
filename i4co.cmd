@echo off
setlocal
rem set mincmd-api-def-file=c:\develop\machinestuff\mincl\machinestuff-openapi.json
set mincmd-base-url=http://127.0.0.1:5000
set mincmd-loglevel=DEBUG
set mincmd-program-name=i4c
python "c:\develop\machinestuff\mincl\mincmd.py" %*
endlocal