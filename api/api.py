# -*- coding: utf-8 -*-
from starlette.responses import JSONResponse

from I4cAPI import I4cApi, I4cApiRouter
from fastapi import Request
from common import apicfg
from common.exceptions import InputValidationError
from endpoints import log, users, root, projects, installations, intfiles, workpiece, tools, batch
import uvicorn
import common

app = I4cApi()
app.include_router(root.router)
app.include_router(log.router, prefix="/log", tags=["log"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(installations.router, prefix="/installations", tags=["installations"])
app.include_router(intfiles.router, prefix="/intfiles", tags=["intfiles"])
app.include_router(workpiece.router, prefix="/workpiece", tags=["workpiece"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])
app.include_router(batch.router, prefix="/batch", tags=["batch"])


# todo: exception-ök kezelése. Kellene valami saját exception és azt kellene eldobálni. Majd erre kellene írni egy
#       custom exception handler-t (https://fastapi.tiangolo.com/tutorial/handling-errors/)
#       pl file letöltésnél ha nincs olyan file akkor meg átfordítani erre


@app.exception_handler(InputValidationError)
async def unicorn_exception_handler(request: Request, exc: InputValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.on_event("startup")
async def startup_event():
    await common.DatabaseConnection.init_db_pool()

if __name__ == "__main__":
    if ("debug" in apicfg) and apicfg["debug"]:
        common.set_debug_mode()
    # http://localhost:5000
    # http://localhost:5000/docs
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info")
