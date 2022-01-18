@echo off
setlocal
set PYTHONPATH=c:\develop\machinestuff\i4c\cli;%PYTHONPATH%
python -m i4c %*
endlocal

