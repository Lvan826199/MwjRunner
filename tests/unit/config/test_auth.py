"""认证配置单元测试。"""

from __future__ import annotations

import base64

import pytest

from mwjrunner.config.model import AuthConfig
from mwjrunner.core.runner import _resolve_auth
from mwjrunner.variables.engine import VariableEngine


@pytest.mark.unit
class TestAuthConfig:
    """AuthConfig 模型测试。"""

    def test_bearer_header_value(self) -> None:
        auth = AuthConfig(type="bearer", token="my-token")
        assert auth.to_header_value() == "Bearer my-token"

    def test_basic_header_value(self) -> None:
        auth = AuthConfig(type="basic", username="user", password="pass")
        expected = base64.b64encode(b"user:pass").decode()
        assert auth.to_header_value() == f"Basic {expected}"

    def test_bearer_no_token_returns_none(self) -> None:
        auth = AuthConfig(type="bearer")
        assert auth.to_header_value() is None

    def test_basic_missing_password_returns_none(self) -> None:
        auth = AuthConfig(type="basic", username="user")
        assert auth.to_header_value() is None

    def test_unknown_type_returns_none(self) -> None:
        auth = AuthConfig(type="oauth2")
        assert auth.to_header_value() is None


@pytest.mark.unit
class TestResolveAuth:
    """_resolve_auth 优先级和变量渲染测试。"""

    def test_case_auth_overrides_global(self) -> None:
        global_auth = AuthConfig(type="bearer", token="global-token")
        case_auth = {"type": "bearer", "token": "case-token"}
        engine = VariableEngine()

        result = _resolve_auth(case_auth, global_auth, engine)

        assert result == "Bearer case-token"

    def test_global_auth_used_when_no_case_auth(self) -> None:
        global_auth = AuthConfig(type="bearer", token="global-token")
        engine = VariableEngine()

        result = _resolve_auth(None, global_auth, engine)

        assert result == "Bearer global-token"

    def test_no_auth_returns_none(self) -> None:
        engine = VariableEngine()
        result = _resolve_auth(None, None, engine)
        assert result is None

    def test_variable_rendering_in_case_auth(self) -> None:
        case_auth = {"type": "bearer", "token": "${my_token}"}
        engine = VariableEngine({"my_token": "rendered-token"})

        result = _resolve_auth(case_auth, None, engine)

        assert result == "Bearer rendered-token"

    def test_variable_rendering_in_global_auth(self) -> None:
        global_auth = AuthConfig(type="bearer", token="${api_token}")
        engine = VariableEngine({"api_token": "resolved-token"})

        result = _resolve_auth(None, global_auth, engine)

        assert result == "Bearer resolved-token"

    def test_basic_auth_case_level(self) -> None:
        case_auth = {"type": "basic", "username": "admin", "password": "secret"}
        engine = VariableEngine()

        result = _resolve_auth(case_auth, None, engine)

        expected = base64.b64encode(b"admin:secret").decode()
        assert result == f"Basic {expected}"
