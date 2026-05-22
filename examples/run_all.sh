#!/bin/bash
# MwjRunner 示例一键运行脚本（Linux/macOS）
# 用途：启动 FastAPI 示例服务，运行所有示例用例，生成报告，停止服务

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== MwjRunner 示例一键运行 ==="
echo ""

echo "[1/4] 安装示例服务依赖..."
cd "$SCRIPT_DIR/api"
uv sync --quiet
echo "  依赖已就绪"

echo "[2/4] 启动 FastAPI 示例服务..."
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
echo "  服务 PID: $API_PID"

echo "  等待服务启动..."
sleep 3

if ! curl -sf http://127.0.0.1:8000/health > /dev/null; then
    echo "  ERROR: 示例服务启动失败"
    kill $API_PID 2>/dev/null || true
    exit 1
fi
echo "  服务已就绪 → http://127.0.0.1:8000"

echo "[3/4] 运行示例用例..."
cd "$PROJECT_ROOT"

echo ""
echo "--- 运行基础示例（smoke 标签）---"
uv run mwjrunner run examples/cases/ \
    --base-url http://127.0.0.1:8000 \
    --tags smoke \
    --report console,json,html || true

echo ""
echo "--- 运行数据驱动示例 ---"
uv run mwjrunner run examples/cases/data_driven/ \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html || true

echo ""
echo "--- 运行断言扩展示例 ---"
uv run mwjrunner run examples/cases/assertions/ \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html || true

echo ""
echo "--- 运行提取器示例 ---"
uv run mwjrunner run examples/cases/extractors/ \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html || true

echo ""
echo "--- 运行认证示例 ---"
uv run mwjrunner run examples/cases/auth/ \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html || true

echo ""
echo "--- 运行变量函数示例 ---"
uv run mwjrunner run examples/cases/variables/ \
    --base-url http://127.0.0.1:8000 \
    --report console,json,html || true

echo "[4/4] 停止示例服务..."
kill $API_PID 2>/dev/null || true
echo "  服务已停止"

echo ""
echo "=== 完成！报告已生成到 reports/ 目录 ==="
ls -1t reports/ | head -6 | while read d; do
    echo "  reports/$d/"
done
