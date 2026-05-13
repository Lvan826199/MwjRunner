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

## 已实现功能

### 用例管理（T41）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/cases` | GET | 用例列表（支持 folder/tags/priority/search 筛选） |
| `/api/cases/folders` | GET | 目录树结构 |
| `/api/cases/{id}` | GET | 用例详情（含 YAML 内容） |
| `/api/cases` | POST | 创建用例 |
| `/api/cases/{id}` | PUT | 更新用例 |
| `/api/cases/{id}` | DELETE | 删除用例 |
| `/api/health` | GET | 健康检查 |

前端页面：
- 仪表盘：统计卡片（用例总数、今日执行、通过率、环境数）
- 用例管理：左侧目录树 + 右侧表格（搜索、筛选、新建、导入、编辑、执行、删除）
- 执行记录：执行历史列表（待实现）
- 环境配置：环境管理（待实现）

## 目录结构

```
platform/
  frontend/       # Vue 3 前端
    src/
      api/        # axios 接口封装
      views/      # 页面组件（Dashboard/Cases/Executions/Environments）
      router/     # Vue Router 路由配置
      App.vue     # 根组件（侧边栏布局）
  backend/        # FastAPI 后端
    app/
      main.py     # 应用入口
      api/        # API 路由（cases.py）
      models/     # SQLAlchemy 模型（case.py）
      schemas/    # Pydantic 模型（case.py）
      services/   # 业务逻辑
      engine/     # 引擎调用封装（subprocess）
      core/       # 配置、数据库初始化
    data/         # SQLite 数据库文件
    storage/      # 用例文件存储
```

## 开发进度

| 任务 | 状态 | 说明 |
|------|------|------|
| T40 平台骨架 | 已完成 | 前后端项目结构、Element Plus、SQLite |
| T41 用例管理 | 已完成 | CRUD API + 前端页面 |
| T42 执行触发 | 待开始 | asyncio 后台任务调用引擎 |
| T43 环境配置 | 待开始 | 环境 CRUD |
| T44 分布式执行 | 待开始 | 多 Worker |
| T45 Mock 服务 | 待开始 | 自动生成 Mock |
| T46 性能基准 | 待开始 | 响应时间趋势 |
| T47 CI/CD | 待开始 | GitHub Actions 等 |
| T48 多租户 | 待开始 | JWT + 权限 |
