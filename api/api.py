# -*- coding: utf-8 -*-
from starlette.responses import JSONResponse
from I4cAPI import I4cApi
from fastapi import Request
from common import apicfg
from common.exceptions import I4cInputValidationError, I4cClientError, I4cClientNotFound, I4cServerError
from endpoints import log, users, root, projects, installations, intfiles, \
    workpiece, tools, batch, alarm, stat, roles, pwdreset, settings, ping, audit
import uvicorn
import common
import models.roles

app = I4cApi()
routers = ((root, None),
           (log, "log"), (users, "users"), (roles, "roles"),
           (projects, "projects"), (installations, "installations"), (intfiles, "intfiles"),
           (workpiece, "workpiece"), (tools, "tools"), (batch, "batch"),
           (alarm, "alarm"), (stat, "stat"), (pwdreset, "pwdreset"),
           (settings, "settings"), (ping, "ping"), (audit, "audit"))
for r in routers:
    if r[1] is None:
        app.include_router(r[0].router)
    else:
        app.include_router(r[0].router, prefix=f"/{r[1]}", tags=[r[1]])

models.roles.path_list = [x for r in routers for x in r[0].router.path_list]


@app.exception_handler(ValueError)
async def unicorn_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"message": str(exc)},
    )


@app.exception_handler(I4cInputValidationError)
async def unicorn_exception_handler(request: Request, exc: I4cInputValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.exception_handler(I4cClientError)
async def unicorn_exception_handler(request: Request, exc: I4cClientError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(I4cClientNotFound)
async def unicorn_exception_handler(request: Request, exc: I4cClientNotFound):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(I4cServerError)
async def unicorn_exception_handler(request: Request, exc: I4cServerError):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.on_event("startup")
async def startup_event():
    await common.DatabaseConnection.init_db_pool()


if __name__ == "__main__":
    if ("debug" in apicfg) and apicfg["debug"]:
        common.set_debug_mode()
    # http://localhost:5000
    # http://localhost:5000/docs
    host = apicfg.get("host", "127.0.0.1")
    port = int(apicfg.get("port", 5000))
    log_level = apicfg.get("log_level", "info")
    workers = int(apicfg.get("workers", 1))
    uvicorn.run(app="api:app", host=host, port=port, log_level=log_level, workers=workers)
