# -*- coding: utf-8 -*-
from starlette.responses import JSONResponse
from I4cAPI import I4cApi
from fastapi import Request
from common import apicfg
from common.exceptions import I4cInputValidationError
from endpoints import log, users, root, projects, installations, intfiles, workpiece, tools, batch, alarm, stat, roles
import uvicorn
import common
import models.roles

app = I4cApi()
routers = ((root, None),
           (log, "log"), (users, "users"), (roles, "roles"),
           (projects, "projects"), (installations, "installations"), (intfiles, "intfiles"),
           (workpiece, "workpiece"), (tools, "tools"), (batch, "batch"),
           (alarm, "alarm"), (stat, "stat"))
for r in routers:
    if r[1] is None:
        app.include_router(r[0].router)
    else:
        app.include_router(r[0].router, prefix=f"/{r[1]}", tags=[r[1]])

models.roles.path_list = [x for r in routers for x in r[0].router.path_list]


# todo: exception-ök kezelése. Kellene valami saját exception és azt kellene eldobálni. Majd erre kellene írni egy
#       custom exception handler-t (https://fastapi.tiangolo.com/tutorial/handling-errors/)
#       pl file letöltésnél ha nincs olyan file akkor meg átfordítani erre


@app.exception_handler(I4cInputValidationError)
async def unicorn_exception_handler(request: Request, exc: I4cInputValidationError):
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
