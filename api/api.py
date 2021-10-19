from fastapi import APIRouter
from endpoints import log
from fastapi import FastAPI
import uvicorn

api_router = APIRouter()
api_router.include_router(log.router, prefix="/log", tags=["log"])

app = FastAPI()
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info")
