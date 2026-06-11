# MwjRunner 示例用例

本目录包含 MwjRunner 各核心功能的完整示例，所有用例均基于 `examples/api/` FastAPI 示例服务设计。

## 目录结构

```text
examples/
├── api/                          # FastAPI 示例接口服务（独立 UV 环境）
├── cases/
│   ├── health.yaml               # 基础健康检查（smoke/P0）
│   ├── health_fail.yaml          # 断言失败演示（negative）
│   ├── login.yaml                # 登录 + token 提取（smoke/auth）
│   ├── login_profile.yaml        # 登录 → token → profile 完整流程
│   ├── quickstart_httpbin.yaml   # 零依赖快速开始（使用 httpbin.org）
│   ├── data_driven/              # 数据驱动示例
│   │   ├── login_inline.yaml     # inline data 字段
│   │   ├── login_csv.yaml        # CSV 文件驱动
│   │   └── login_json.yaml       # JSON 文件驱动
│   ├── variables/
│   │   └── builtin_functions.yaml # 内置变量函数（timestamp/uuid/random）
│   ├── assertions/               # 断言扩展示例
│   │   ├── response_time.yaml    # 响应时间断言
│   │   ├── regex.yaml            # 正则断言
│   │   ├── header_cookie.yaml    # Header 断言
│   │   └── json_schema.yaml      # JSON Schema 断言
│   ├── extractors/               # 提取器扩展示例
│   │   ├── header_cookie.yaml    # Header 提取器
│   │   └── regex.yaml            # 正则提取器
│   ├── hooks/
│   │   └── before_after_case.yaml # Hooks 生命周期示例
│   ├── auth/
│   │   └── bearer_auth.yaml      # Bearer 认证内置示例
│   └── advanced/                 # 高级功能示例
│       ├── retry_demo.yaml       # 失败重试演示
│       └── fail_fast_demo.yaml   # fail-fast 演示
├── data/                         # 数据文件
│   ├── users.csv                 # 数据驱动 CSV 数据
│   ├── users.json                # 数据驱动 JSON 数据
│   └── sample.txt                # 文件上传示例文件
├── envs/                         # 环境配置文件
│   ├── dev.yaml                  # 开发环境（http://127.0.0.1:8000）
│   ├── test.yaml                 # 测试环境
│   └── prod.yaml                 # 生产环境
├── hooks/                        # Hook 函数实现
│   ├── __init__.py
│   └── auth_hook.py              # 示例 hook：注入 token
├── mwjrunner.yaml                # 质量门禁配置示例
├── run_all.sh                    # 一键运行脚本（Linux/macOS）
└── run_all.bat                   # 一键运行脚本（Windows）
```

---

## 快速开始

### 第 1 步：启动 FastAPI 示例服务

```bash
cd examples/api
uv sync
uv run uvicorn app.main:app --reload
```

确认服务正常：

```bash
curl http://127.0.0.1:8000/health
# 预期: {"status":"ok"}
```

### 第 2 步：运行基础示例（另开终端）

```bash
# 回到项目根目录
cd ../..

# 运行健康检查用例
uv run mwjrunner run examples/cases/health.yaml \
    --base-url http://127.0.0.1:8000 \
    --report console

# 运行完整登录流程
uv run mwjrunner run examples/cases/login_profile.yaml \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html
```

### 第 3 步：一键运行所有示例

**Linux/macOS**：

```bash
bash examples/run_all.sh
```

**Windows**：

```bat
examples\run_all.bat
```

---

## 按功能运行

### 基础用例（smoke）

```bash
uv run mwjrunner run examples/cases/ \
    --base-url http://127.0.0.1:8000 \
    --tags smoke \
    --report console,json,html
```

### 按优先级过滤

```bash
# 只运行 P0 级用例
uv run mwjrunner run examples/cases/ \
    --base-url http://127.0.0.1:8000 \
    --priority P0 \
    --report console

# 排除负向用例
uv run mwjrunner run examples/cases/ \
    --base-url http://127.0.0.1:8000 \
    --exclude-tags negative \
    --report console
```

### 数据驱动

```bash
# inline data
uv run mwjrunner run examples/cases/data_driven/login_inline.yaml \
    --base-url http://127.0.0.1:8000 --report console

# CSV 文件驱动
uv run mwjrunner run examples/cases/data_driven/login_csv.yaml \
    --base-url http://127.0.0.1:8000 --report console

# JSON 文件驱动
uv run mwjrunner run examples/cases/data_driven/login_json.yaml \
    --base-url http://127.0.0.1:8000 --report console
```

### 变量函数

```bash
uv run mwjrunner run examples/cases/variables/builtin_functions.yaml \
    --base-url http://127.0.0.1:8000 --report console
```

### 环境配置

```bash
# 使用 --env 参数，自动读取 examples/envs/dev.yaml
# 注意：--env 在当前工作目录的 envs/ 子目录下查找，需先进入 examples/ 目录
cd examples
uv run mwjrunner run cases/login.yaml \
    --env dev \
    --report console
```

### 断言扩展

```bash
uv run mwjrunner run examples/cases/assertions/ \
    --base-url http://127.0.0.1:8000 --report console
```

### 提取器扩展

```bash
uv run mwjrunner run examples/cases/extractors/ \
    --base-url http://127.0.0.1:8000 --report console
```

### Hooks 生命周期

```bash
uv run mwjrunner run examples/cases/hooks/before_after_case.yaml \
    --base-url http://127.0.0.1:8000 --report console
```

### 内置认证方案

```bash
# Bearer 认证：auth 字段自动注入 Authorization header
uv run mwjrunner run examples/cases/auth/bearer_auth.yaml \
    --base-url http://127.0.0.1:8000 --report console
```

### 重试

```bash
# 演示失败重试（请求 /api/error 固定返回 500，重试 2 次、共 3 次尝试）
uv run mwjrunner run examples/cases/advanced/retry_demo.yaml \
    --base-url http://127.0.0.1:8000 --report console
```

### fail-fast

```bash
# fail-fast 是用例级行为：某个用例失败后，跳过目录中后续用例
# （同一用例内的步骤不会因断言失败中断）
uv run mwjrunner run examples/cases/advanced/ \
    --base-url http://127.0.0.1:8000 --fail-fast --report console
```

### 并发执行

```bash
# --workers 4：4 个线程并发执行
uv run mwjrunner run examples/cases/ \
    --base-url http://127.0.0.1:8000 \
    --tags smoke \
    --workers 4 \
    --report console
```

### 质量门禁

```bash
# examples/mwjrunner.yaml 配置了 max_failure_rate: 0.1
# 失败率超过 10% 时退出码为 4
# 注意：mwjrunner.yaml 从当前工作目录读取，需先进入 examples/ 目录
cd examples
uv run mwjrunner run cases/ \
    --base-url http://127.0.0.1:8000 \
    --report console
```

---

## 退出码说明

| 退出码 | 含义 |
|--------|------|
| 0 | 所有用例通过 |
| 1 | 存在断言失败 |
| 2 | 执行错误（加载/配置/网络等） |
| 3 | 引擎内部错误 |
| 4 | 质量门禁不通过 |

---

## 常见问题

**Q: 启动服务时报端口占用**

```bash
# 查找占用 8000 端口的进程
# Linux/macOS
lsof -i :8000
# Windows
netstat -ano | findstr :8000
```

**Q: 数据驱动用例提示找不到数据文件**

数据文件路径是相对于 YAML 用例文件所在目录解析的。例如 `login_csv.yaml` 在 `examples/cases/data_driven/`，数据文件路径写 `../../data/users.csv` 才能正确找到 `examples/data/users.csv`。

**Q: Hook 函数找不到**

Hook 函数通过 Python 模块路径引用，需确保：
1. `examples/hooks/__init__.py` 存在（标记为 Python 包）
2. 在项目根目录运行 `uv run mwjrunner`（而不是在 examples/ 目录下）
3. 或者将 `examples/` 目录加入 `PYTHONPATH`
