"""示例 Hook 函数，用于演示 MwjRunner hooks 机制。"""


def inject_token(context: dict) -> None:
    """在 case 执行前注入预设 token，模拟认证准备。"""
    context["injected_token"] = "demo-token"
    context["hook_executed"] = "before_case"


def cleanup(context: dict) -> None:
    """在 case 执行后清理临时变量。"""
    context.pop("hook_executed", None)
