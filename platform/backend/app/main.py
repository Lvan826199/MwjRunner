"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router
from app.api.executions import router as executions_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库。"""
    await init_db()
    yield


app = FastAPI(
    title="MwjRunner Platform",
    description="MwjRunner 接口自动化测试平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases_router)
app.include_router(executions_router)


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "service": "mwjrunner-platform"}
