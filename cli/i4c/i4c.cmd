@echo off
setlocal

rem enable if you want to use downloaded def, and set to the file location, preferably full path
rem set mincmd-api-def-file=c:\program files\i4c\i4c-openapi.json

rem set to the API location. REQUIRED.
set mincmd-base-url=http://127.0.0.1:5000

rem log level DEBUG, default
rem set mincmd-loglevel=DEBUG

set mincmd-program-name=i4c
python "%~dp0mincmd.py" %*
endlocal