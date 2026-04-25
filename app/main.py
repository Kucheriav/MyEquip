from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import engine, Base
from app.routers import (
    user_router, club_router, category_router, parameter_router,
    value_router, storage_router, item_router, distribution_router,
    breakdown_router, item_parameter_value_router
)


logger = logging.getLogger(__name__)
logger.info("FastAPI starting...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="MyEquip API",
    description="Equipment rental and tracking system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_router.router)
app.include_router(club_router.router)
app.include_router(category_router.router)
app.include_router(parameter_router.router)
app.include_router(value_router.router)
app.include_router(storage_router.router)
app.include_router(item_router.router)
app.include_router(distribution_router.router)
app.include_router(breakdown_router.router)
app.include_router(item_parameter_value_router.router)


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "MyEquip API",
        "docs": "/docs",
        "openapi_schema": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)