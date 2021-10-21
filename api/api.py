import asyncpg
from fastapi import APIRouter

from common import dbcfg
from endpoints import log
from fastapi import FastAPI
import uvicorn
import common

api_router = APIRouter()
api_router.include_router(log.router, prefix="/log", tags=["log"])

app = FastAPI()
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    await common.DatabaseConnection.init_db_pool()

if __name__ == "__main__":
    common.set_debug_mode()
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info")
