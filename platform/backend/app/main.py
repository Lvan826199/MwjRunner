"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.benchmarks import router as benchmarks_router
from app.api.cases import router as cases_router
from app.api.ci_templates import router as ci_templates_router
from app.api.environments import router as environments_router
from app.api.executions import router as executions_router
from app.api.mocks import router as mocks_router
from app.api.notifications import router as notifications_router
from app.api.perf import router as perf_router
from app.api.pipelines import router as pipelines_router
from app.api.scenarios import router as scenarios_router
from app.api.stats import router as stats_router
from app.api.users import router as users_router
from app.api.webhooks import router as webhooks_router
from app.api.workers import router as workers_router
from app.api.ws import router as ws_router
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

app.include_router(benchmarks_router)
app.include_router(cases_router)
app.include_router(ci_templates_router)
app.include_router(environments_router)
app.include_router(executions_router)
app.include_router(mocks_router)
app.include_router(notifications_router)
app.include_router(perf_router)
app.include_router(pipelines_router)
app.include_router(scenarios_router)
app.include_router(stats_router)
app.include_router(users_router)
app.include_router(webhooks_router)
app.include_router(workers_router)
app.include_router(ws_router)


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "service": "mwjrunner-platform"}
