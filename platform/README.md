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
| `/api/executions` | GET | 执行记录列表（支持 status 筛选） |
| `/api/executions/{id}` | GET | 执行详情（含 stdout/stderr） |
| `/api/executions` | POST | 触发执行（后台 asyncio 调用引擎） |
| `/api/executions/{id}/report` | GET | 获取 JSON 报告 |
| `/api/environments` | GET | 环境列表 |
| `/api/environments/{id}` | GET | 环境详情 |
| `/api/environments` | POST | 创建环境 |
| `/api/environments/{id}` | PUT | 更新环境 |
| `/api/environments/{id}` | DELETE | 删除环境 |
| `/api/environments/{id}/clone` | POST | 克隆环境 |
| `/api/workers` | GET | Worker 列表（自动标记超时离线） |
| `/api/workers/register` | POST | Worker 注册（幂等） |
| `/api/workers/heartbeat` | POST | Worker 心跳上报 |
| `/api/workers/{worker_id}` | DELETE | 移除 Worker |
| `/api/workers/dispatch` | POST | 分布式执行（自动分片分发） |
| `/api/workers/shards/{execution_id}` | GET | 获取分片列表 |
| `/api/workers/shards/report` | POST | 分片结果上报 |
| `/api/mocks` | GET | Mock 规则列表 |
| `/api/mocks/{id}` | GET | Mock 规则详情 |
| `/api/mocks` | POST | 创建 Mock 规则 |
| `/api/mocks/{id}` | PUT | 更新 Mock 规则 |
| `/api/mocks/{id}` | DELETE | 删除 Mock 规则 |
| `/api/mocks/generate` | POST | 从用例自动生成 Mock 规则 |
| `/api/mocks/{id}/reset-hits` | POST | 重置命中计数 |
| `/api/benchmarks` | GET | 压测记录列表 |
| `/api/benchmarks/{id}` | GET | 压测详情 |
| `/api/benchmarks` | POST | 创建并启动压测 |
| `/api/benchmarks/{id}` | DELETE | 删除压测记录 |
| `/api/pipelines` | GET | Pipeline 列表 |
| `/api/pipelines/{id}` | GET | Pipeline 详情 |
| `/api/pipelines` | POST | 创建 Pipeline |
| `/api/pipelines/{id}` | PUT | 更新 Pipeline |
| `/api/pipelines/{id}` | DELETE | 删除 Pipeline |
| `/api/pipelines/{id}/trigger` | POST | 触发 Pipeline 执行 |
| `/api/pipelines/{id}/runs` | GET | Pipeline 执行记录 |
| `/api/pipelines/{id}/badge` | GET | 通过率 SVG 徽章 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/logout` | POST | 用户登出 |
| `/api/auth/me` | GET | 当前用户信息 |
| `/api/users` | GET | 用户列表 |
| `/api/users` | POST | 创建用户 |
| `/api/users/{id}` | PUT | 更新用户 |
| `/api/users/{id}` | DELETE | 删除用户 |
| `/api/teams` | GET | 团队列表 |
| `/api/teams` | POST | 创建团队 |
| `/api/teams/{id}` | PUT | 更新团队 |
| `/api/teams/{id}` | DELETE | 删除团队 |
| `/api/health` | GET | 健康检查 |

前端页面：
- 仪表盘：统计卡片（用例总数、今日执行、通过率、环境数）
- 用例管理：左侧目录树 + 右侧表格（搜索、筛选、新建、导入、编辑、执行、删除）
- 执行记录：执行历史表格 + 详情抽屉（统计、stdout/stderr）
- 环境配置：卡片网格 + 详情抽屉（认证、Headers、Variables）
- Worker 监控：统计卡片 + 节点网格（状态/并发/心跳），10秒自动刷新
- Mock 服务：规则表格（方法/路径/状态码/命中数）+ 新建/编辑抽屉
- 性能压测：压测记录表格 + 新建对话框 + 详情抽屉（延迟分布/错误分布）
- CI/CD：Pipeline 卡片网格 + 触发执行 + 执行记录抽屉 + SVG 徽章
- 用户权限：用户表格 + 团队卡片网格 + Tab 切换 + 认证登录

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
| T42 执行触发 | 已完成 | asyncio 后台任务 + 执行记录 + 详情抽屉 |
| T43 环境配置 | 已完成 | CRUD + 克隆 + 卡片网格 + 认证/Headers/Variables |
| T44 分布式执行 | 已完成 | Worker 注册/心跳 + 任务分片 + 监控页面 |
| T45 Mock 服务 | 已完成 | 规则 CRUD + 用例自动生成 + 命中计数 + 管理页面 |
| T46 性能基准 | 已完成 | 并发压测 + P50/P90/P95/P99 + RPS + 错误分布 |
| T47 CI/CD | 已完成 | Pipeline CRUD + 触发 + 执行记录 + SVG 徽章 |
| T48 多租户 | 已完成 | 用户认证 + 角色权限 + 团队管理 |
| T49 JWT 认证 | 已完成 | PyJWT 双 Token + bcrypt + 黑名单 |
| T50 数据权限隔离 | 已完成 | RBAC + team_id 过滤 + 资源鉴权 |
| T51 前端登录守卫 | 已完成 | Pinia 认证 + 路由守卫 + Token 自动刷新 |
| T52 仪表盘真实化 | 已完成 | 统计 API + ECharts 图表 |
| T53 报告可视化 | 已完成 | 执行详情页 + 统计饼图 + 步骤表格 |
| T54 WebSocket 推送 | 已完成 | 团队隔离广播 + 自动重连 + 心跳 |
| T55 CI 模板生成 | 已完成 | GitHub Actions / GitLab CI / Jenkins |
| T56 Webhook 触发 | 已完成 | GitHub/GitLab/通用 Webhook + 签名验证 |
| T57 通知增强 | 已完成 | 钉钉/飞书/Slack/邮件 + 连通性测试 |
| T58 gRPC 支持 | 已完成 | Unary + Streaming + Reflection |
| T59 场景编排 | 已完成 | 多用例串联 + 变量传递 + 延迟控制 |
| T60 性能基线 | 已完成 | 基线管理 + 对比 + 回归检测 |
