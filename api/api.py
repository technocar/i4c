from I4cAPI import I4cApi, I4cApiRouter
from endpoints import log, users, root, projects, installations
import uvicorn
import common

api_router = I4cApiRouter()
api_router.include_router(root.router)
api_router.include_router(log.router, prefix="/log", tags=["log"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(installations.router, prefix="/installations", tags=["installations"])

app = I4cApi()
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    await common.DatabaseConnection.init_db_pool()

if __name__ == "__main__":
    common.set_debug_mode()
    # http://localhost:5000
    # http://localhost:5000/docs
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info")
