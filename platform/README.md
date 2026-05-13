# MwjRunner Platform

MwjRunner 接口自动化测试平台 — Web 管理界面。

与 MwjRunner 引擎完全分离，通过 subprocess 调用引擎 CLI。

## 技术栈

- 前端：Vue 3 + TypeScript + Element Plus + Pinia + Vue Router
- 后端：FastAPI + SQLAlchemy + SQLite
- 引擎调用：subprocess（`mwjrunner run`）

## 快速启动

### 后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --port 8080 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端访问 http://localhost:3000，API 代理到后端 http://localhost:8080。

## 目录结构

```
platform/
  frontend/       # Vue 3 前端
  backend/        # FastAPI 后端
    app/
      main.py     # 应用入口
      api/        # API 路由
      models/     # 数据库模型
      schemas/    # Pydantic 模型
      services/   # 业务逻辑
      engine/     # 引擎调用封装
      core/       # 配置和数据库
    data/         # SQLite 数据库
    storage/      # 用例文件存储
```
