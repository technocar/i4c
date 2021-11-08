from I4cAPI import I4cApi, I4cApiRouter
from common import apicfg
from endpoints import log, users, root, projects, installations, intfiles, workpiece, tools
import uvicorn
import common

api_router = I4cApiRouter()
api_router.include_router(root.router)
api_router.include_router(log.router, prefix="/log", tags=["log"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(installations.router, prefix="/installations", tags=["installations"])
api_router.include_router(intfiles.router, prefix="/intfiles", tags=["intfiles"])
api_router.include_router(workpiece.router, prefix="/workpiece", tags=["workpiece"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])

app = I4cApi()
app.include_router(api_router)

# todo: log all api calls to log table for audit
# todo: smarter string match when listing object.
#       két mód:
#       (1) teljes egyezés
#       (2) multi param, item-enként pipe-os match? elül-hátul 0-1 pipe lehet. Középen meg pipe-ot jelent. Pipe escape nincs.


@app.on_event("startup")
async def startup_event():
    await common.DatabaseConnection.init_db_pool()

if __name__ == "__main__":
    if ("debug" in apicfg) and apicfg["debug"]:
        common.set_debug_mode()
    # http://localhost:5000
    # http://localhost:5000/docs
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info")
