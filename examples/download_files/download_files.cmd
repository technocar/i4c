@echo off

set installation=1

mkdir gom

echo GETTING INFO ON INSTALLATION %installation%

call i4c installation list --id %installation% --output-template "{- for f in value[0].files -}{{f}}{{nl}}{- endfor -}" --output-file files.txt

echo DOWNLOADING FILES:
type files.txt
echo.

call i4c installation file --id %installation% --input-data @files.txt --input-format lines --input-foreach $[*] --$savepath $ --output-file {{origin}}

del files.txt