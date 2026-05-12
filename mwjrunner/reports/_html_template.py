"""HTML 报告模板渲染。"""

from __future__ import annotations

import html
import json
from typing import Any

_CSS = """\
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  line-height:1.6;color:#1a1a1a;background:#f5f5f5;padding:24px;max-width:1200px;margin:0 auto}
h1{font-size:1.5rem;margin-bottom:4px}
.meta{color:#666;font-size:0.85rem;margin-bottom:20px}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.card h3{font-size:0.8rem;text-transform:uppercase;color:#666;margin-bottom:4px}
.card .value{font-size:1.4rem;font-weight:700}
.passed{color:#16a34a}.failed{color:#ea580c}.error{color:#dc2626}
.case{background:#fff;border-radius:8px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden}
.case>summary{padding:12px 16px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:8px}
.case>summary .badge{font-size:0.75rem;padding:2px 8px;border-radius:4px;color:#fff;font-weight:500}
.badge-passed{background:#16a34a}.badge-failed{background:#ea580c}.badge-error{background:#dc2626}
.case-body{padding:0 16px 16px}
.step{border:1px solid #e5e5e5;border-radius:6px;margin-top:12px;overflow:hidden}
.step>summary{padding:10px 12px;cursor:pointer;font-weight:500;
  display:flex;align-items:center;gap:8px;background:#fafafa}
.section-title{font-size:0.8rem;font-weight:600;color:#666;margin:12px 0 6px;text-transform:uppercase}
pre{background:#f8f8f8;border:1px solid #e5e5e5;border-radius:4px;padding:10px;
  overflow-x:auto;font-size:0.82rem;white-space:pre-wrap;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:0.85rem;margin-bottom:8px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #e5e5e5}
th{background:#fafafa;font-weight:600}
.err-list{background:#fef2f2;border:1px solid #fecaca;border-radius:4px;
  padding:10px;margin-top:8px;font-size:0.85rem;color:#991b1b}
footer{margin-top:32px;text-align:center;color:#999;font-size:0.8rem}
@media print{details{open:true !important}body{background:#fff;padding:0}}
"""
def _esc(value: Any) -> str:
    """转义任意值为 HTML 安全字符串。"""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def render_html_report(data: dict[str, Any]) -> str:
    """从 RunResult.to_dict() 数据渲染完整 HTML 报告。"""
    parts = [
        _render_doctype_and_head(data),
        '<body>',
        _render_header(data),
        _render_summary(data.get("summary", {})),
        _render_run_errors(data.get("errors", [])),
        _render_cases(data.get("cases", [])),
        _render_footer(),
        '</body></html>',
    ]
    return "\n".join(parts)


def _render_doctype_and_head(data: dict[str, Any]) -> str:
    run_id = _esc(data.get("run_id", ""))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MwjRunner 测试报告 - {run_id}</title>
<style>{_CSS}</style>
</head>"""


def _render_header(data: dict[str, Any]) -> str:
    run_id = _esc(data.get("run_id", ""))
    started = _esc(data.get("started_at", ""))
    ended = _esc(data.get("ended_at", ""))
    elapsed = data.get("summary", {}).get("elapsed_ms", 0)
    return f"""<h1>MwjRunner 测试报告</h1>
<p class="meta">run_id: {run_id} | 开始: {started} | 结束: {ended} | 耗时: {elapsed:.1f} ms</p>"""


def _render_summary(summary: dict[str, Any]) -> str:
    def _card(title: str, value: Any, css_class: str = "") -> str:
        cls = f' class="{css_class}"' if css_class else ""
        return f'<div class="card"><h3>{_esc(title)}</h3><div class="value"{cls}>{_esc(str(value))}</div></div>'

    total_cases = summary.get("total_cases", 0)
    passed_cases = summary.get("passed_cases", 0)
    failed_cases = summary.get("failed_cases", 0)
    error_cases = summary.get("error_cases", 0)
    total_steps = summary.get("total_steps", 0)
    passed_steps = summary.get("passed_steps", 0)
    failed_steps = summary.get("failed_steps", 0)
    error_steps = summary.get("error_steps", 0)
    total_assertions = summary.get("total_assertions", 0)
    failed_assertions = summary.get("failed_assertions", 0)
    total_errors = summary.get("total_errors", 0)

    cards = [
        _card("总用例", total_cases),
        _card("通过用例", passed_cases, "passed"),
        _card("失败用例", failed_cases, "failed" if failed_cases else ""),
        _card("错误用例", error_cases, "error" if error_cases else ""),
        _card("总步骤", total_steps),
        _card("通过步骤", passed_steps, "passed"),
        _card("失败步骤", failed_steps, "failed" if failed_steps else ""),
        _card("错误步骤", error_steps, "error" if error_steps else ""),
        _card("总断言", total_assertions),
        _card("失败断言", failed_assertions, "failed" if failed_assertions else ""),
        _card("总错误", total_errors, "error" if total_errors else ""),
    ]
    return '<div class="summary">\n' + "\n".join(cards) + "\n</div>"


def _render_run_errors(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "\n".join(f"<li>{_esc(e)}</li>" for e in errors)
    return f'<div class="err-list"><strong>运行级错误\uff1a</strong><ul>{items}</ul></div>'


def _render_cases(cases: list[dict[str, Any]]) -> str:
    if not cases:
        return '<p>无用例结果。</p>'
    return "\n".join(_render_case(case) for case in cases)


def _render_case(case: dict[str, Any]) -> str:
    name = _esc(case.get("name", ""))
    status = case.get("status", "passed")
    source = _esc(case.get("source_file", ""))
    badge_cls = f"badge badge-{status}"
    open_attr = " open" if status != "passed" else ""
    steps_html = "\n".join(_render_step(step) for step in case.get("steps", []))
    errors_html = _render_case_errors(case.get("errors", []))
    return f"""<details class="case"{open_attr}>
<summary><span class="{badge_cls}">{_esc(status)}</span> {name} <span class="meta">({source})</span></summary>
<div class="case-body">
{steps_html}
{errors_html}
</div>
</details>"""


def _render_case_errors(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "\n".join(f"<li>{_esc(e)}</li>" for e in errors)
    return f'<div class="err-list"><strong>用例错误\uff1a</strong><ul>{items}</ul></div>'


def _render_step(step: dict[str, Any]) -> str:
    name = _esc(step.get("name", ""))
    status = step.get("status", "passed")
    elapsed = step.get("elapsed_ms", 0)
    badge_cls = f"badge badge-{status}"
    open_attr = " open" if status != "passed" else ""

    sections = []
    sections.append(_render_request_section(step.get("request")))
    sections.append(_render_response_section(step.get("response")))
    sections.append(_render_assertions_section(step.get("assertions", [])))
    sections.append(_render_extracts_section(step.get("extracts", [])))
    sections.append(_render_step_errors(step.get("errors", [])))

    body = "\n".join(s for s in sections if s)
    return f"""<details class="step"{open_attr}>
<summary><span class="{badge_cls}">{_esc(status)}</span> {name} <span class="meta">({elapsed:.1f} ms)</span></summary>
<div style="padding:10px 12px">
{body}
</div>
</details>"""


def _render_request_section(request: dict[str, Any] | None) -> str:
    if not request:
        return ""
    method = _esc(request.get("method", ""))
    url = _esc(request.get("url", ""))
    headers = request.get("headers", {})
    body = request.get("body")
    timeout = request.get("timeout")

    parts = ['<p class="section-title">Request</p>']
    parts.append(f"<pre>{method} {url}")
    if headers:
        for k, v in headers.items():
            parts.append(f"{_esc(k)}: {_esc(v)}")
    if timeout:
        parts.append(f"Timeout: {timeout}s")
    parts.append("</pre>")
    if body:
        formatted = _format_json_body(body)
        parts.append(f"<pre>{_esc(formatted)}</pre>")
    return "\n".join(parts)


def _render_response_section(response: dict[str, Any] | None) -> str:
    if not response:
        return ""
    status_code = response.get("status_code", "")
    elapsed = response.get("elapsed_ms", 0)
    headers = response.get("headers", {})
    body = response.get("body")

    parts = [f'<p class="section-title">Response ({_esc(str(status_code))}, {elapsed:.1f} ms)</p>']
    if headers:
        header_lines = "\n".join(f"{_esc(k)}: {_esc(v)}" for k, v in headers.items())
        parts.append(f"<pre>{header_lines}</pre>")
    if body:
        formatted = _format_json_body(body)
        parts.append(f"<pre>{_esc(formatted)}</pre>")
    return "\n".join(parts)


def _render_assertions_section(assertions: list[dict[str, Any]]) -> str:
    if not assertions:
        return ""
    rows = []
    for a in assertions:
        passed = a.get("passed", False)
        status_icon = "&#10004;" if passed else "&#10008;"
        css = "passed" if passed else "failed"
        rows.append(
            f'<tr><td class="{css}">{status_icon}</td>'
            f"<td>{_esc(a.get('type', ''))}</td>"
            f"<td>{_esc(a.get('path', ''))}</td>"
            f"<td>{_esc(str(a.get('expected', '')))}</td>"
            f"<td>{_esc(str(a.get('actual', '')))}</td>"
            f"<td>{_esc(a.get('message', ''))}</td></tr>"
        )
    return f"""<p class="section-title">Assertions</p>
<table>
<tr><th></th><th>类型</th><th>路径</th><th>期望</th><th>实际</th><th>消息</th></tr>
{"".join(rows)}
</table>"""


def _render_extracts_section(extracts: list[dict[str, Any]]) -> str:
    if not extracts:
        return ""
    rows = []
    for e in extracts:
        extracted = "&#10004;" if e.get("extracted", False) else "&#10008;"
        rows.append(
            f"<tr><td>{extracted}</td>"
            f"<td>{_esc(e.get('name', ''))}</td>"
            f"<td>{_esc(e.get('path', ''))}</td>"
            f"<td>{_esc(str(e.get('value', '')))}</td>"
            f"<td>{_esc(e.get('message', ''))}</td></tr>"
        )
    return f"""<p class="section-title">Extracts</p>
<table>
<tr><th></th><th>变量名</th><th>路径</th><th>值</th><th>消息</th></tr>
{"".join(rows)}
</table>"""


def _render_step_errors(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "\n".join(f"<li>{_esc(e)}</li>" for e in errors)
    return f'<div class="err-list"><ul>{items}</ul></div>'


def _render_footer() -> str:
    return '<footer>Generated by MwjRunner</footer>'


def _format_json_body(body: Any) -> str:
    """尝试格式化 JSON body, 失败则原样返回。"""
    if not isinstance(body, str):
        return str(body)
    try:
        parsed = json.loads(body)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return body
