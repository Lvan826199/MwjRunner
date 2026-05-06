# MwjRunner FastAPI 示例服务

这是 MwjRunner 的示例被测接口服务，位于仓库内 `examples/api/`，使用 UV 单独管理环境。

该服务用于支撑：

- `doc/使用手册.md` 中的接口示例。
- 后续 `examples/cases/` 中的 MwjRunner YAML 示例用例。
- MwjRunner 引擎开发时的本地 HTTP 请求、断言、变量提取和报告验证。

## 1. 环境要求

- Python `>=3.13`
- UV

检查命令：

```bash
python --version
uv --version
```

## 2. 安装依赖

在仓库根目录进入示例服务目录：

```bash
cd examples/api
```

安装依赖：

```bash
uv sync
```

预期结果：UV 完成依赖解析和安装，没有报错。

## 3. 启动服务

```bash
uv run uvicorn app.main:app --reload
```

预期结果类似：

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

## 4. 检查健康状态

在另一个终端执行：

```bash
curl http://127.0.0.1:8000/health
```

预期响应：

```json
{"status":"ok"}
```

## 5. 示例接口

### GET /health

用途：健康检查。

响应：

```json
{
  "status": "ok"
}
```

### POST /api/login

用途：登录并返回 token。

请求：

```json
{
  "username": "demo",
  "password": "123456"
}
```

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "demo-token"
  }
}
```

### GET /api/profile

用途：携带 token 获取用户信息。

请求头：

```http
Authorization: Bearer demo-token
```

成功响应：

```json
{
  "code": 0,
  "data": {
    "username": "demo",
    "nickname": "示例用户"
  }
}
```

### GET /api/items

用途：查询示例数据，可选 query 参数 `keyword`。

请求示例：

```bash
curl "http://127.0.0.1:8000/api/items?keyword=book"
```

响应示例：

```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "book",
      "price": 39.9
    }
  ]
}
```

### POST /api/items

用途：携带 token 创建示例数据。

请求头：

```http
Authorization: Bearer demo-token
Content-Type: application/json
```

请求体：

```json
{
  "name": "pen",
  "price": 9.9
}
```

成功响应状态码为 `201`，响应示例：

```json
{
  "code": 0,
  "message": "created",
  "data": {
    "id": 4,
    "name": "pen",
    "price": 9.9
  }
}
```

### GET /api/error

用途：固定错误响应，用于演示断言失败和错误报告。

响应状态码为 `500`，响应：

```json
{
  "code": 50001,
  "message": "示例错误"
}
```

## 6. 运行测试

示例服务自身测试使用 pytest。pytest 只用于示例服务开发测试，不属于 MwjRunner 核心执行、断言或报告链路。

```bash
uv run pytest
```

预期结果：所有测试通过。
