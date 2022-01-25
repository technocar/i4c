$src_api_path="..\api\"
$src_web_path=".\dist\"
$dest_api_path="\\karatnetsrv\Karatnet\machinestuff\i4c\api\"
$dest_web_path="\\karatnetsrv\Karatnet\machinestuff\i4c\web\"
$dest_iis_path="\\karatnetsrv\i4c_web\"

Invoke-Expression "ng build --configuration=production"

Copy-Item -Path $src_api_path"*" -Destination $dest_api_path -Exclude @("__pycache__", "internal_file", "log", "*.yaml", "*.cmd") -Force -Confirm:$false -Recurse
Remove-Item $dest_web_path"*" -Force -Confirm:$false -Recurse
Copy-Item -Path $src_web_path"*" -Destination $dest_web_path -Recurse
Remove-Item $dest_iis_path"*" -Exclude "web.config" -Force -Confirm:$false -Recurse
Copy-Item -Path $src_web_path"*" -Destination $dest_iis_path -Recurse
