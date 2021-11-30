rem this needs uvicorn to be on the path
rem kinda tricky, each python version has its own mechanism and locations

uvicorn api:app --port 5000
