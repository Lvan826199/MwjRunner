"""HTML 报告模板渲染。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TEMPLATE_PATH = Path(__file__).parent / "template.html"
_PLACEHOLDER = '"__REPORT_DATA_PLACEHOLDER__"'


def render_html_report(data: dict[str, Any]) -> str:
    """从 RunResult.to_dict() 数据渲染完整 HTML 报告。

    读取 template.html 模板，将占位符替换为实际 JSON 数据。
    对 JSON 中的 </script> 进行转义，防止提前关闭 script 标签。
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    # JSON 中 "<" 只会出现在字符串里，统一转义为 unicode 形式（JSON 字符串内合法转义），
    # 防止 </script>、<script、<!-- 等序列破坏 HTML script 解析状态
    json_str = json_str.replace("<", "\\u003c")
    return template.replace(_PLACEHOLDER, json_str, 1)
