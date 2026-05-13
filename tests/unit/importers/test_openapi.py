"""OpenAPI 用例生成器单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mwjrunner.importers.openapi import generate_from_openapi


SAMPLE_OPENAPI_V3 = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/api/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "获取用户列表",
                "tags": ["users"],
                "parameters": [
                    {"name": "page", "in": "query", "example": 1},
                    {"name": "X-Token", "in": "header"},
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "createUser",
                "summary": "创建用户",
                "tags": ["users"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "age": {"type": "integer"},
                                },
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
    },
}


@pytest.mark.unit
class TestOpenAPIGenerator:
    """OpenAPI 用例生成器测试。"""

    def test_generates_files(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(SAMPLE_OPENAPI_V3), encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = generate_from_openapi(spec_file, output_dir)

        assert len(generated) == 2

    def test_get_case_structure(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(SAMPLE_OPENAPI_V3), encoding="utf-8")

        output_dir = tmp_path / "output"
        generate_from_openapi(spec_file, output_dir)

        case = yaml.safe_load((output_dir / "get_api_users.yaml").read_text(encoding="utf-8"))
        assert case["name"] == "获取用户列表"
        assert case["tags"] == ["users"]
        assert case["steps"][0]["request"]["method"] == "GET"
        assert case["steps"][0]["request"]["url"] == "/api/users"
        assert case["steps"][0]["request"]["query"]["page"] == "1"
        assert case["steps"][0]["request"]["headers"]["X-Token"] == "${X-Token}"
        assert case["steps"][0]["assertions"][0]["expected"] == 200

    def test_post_case_with_body(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(SAMPLE_OPENAPI_V3), encoding="utf-8")

        output_dir = tmp_path / "output"
        generate_from_openapi(spec_file, output_dir)

        case = yaml.safe_load((output_dir / "post_api_users.yaml").read_text(encoding="utf-8"))
        assert case["steps"][0]["request"]["method"] == "POST"
        assert case["steps"][0]["request"]["json"]["email"] == "user@example.com"
        assert case["steps"][0]["request"]["json"]["age"] == 1
        assert case["steps"][0]["assertions"][0]["expected"] == 201

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            generate_from_openapi(tmp_path / "missing.json", tmp_path / "out")

    def test_swagger_v2(self, tmp_path: Path) -> None:
        spec = {
            "swagger": "2.0",
            "basePath": "/v1",
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health Check",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = generate_from_openapi(spec_file, output_dir)

        assert len(generated) == 1
        case = yaml.safe_load(generated[0].read_text(encoding="utf-8"))
        assert case["steps"][0]["request"]["url"] == "/v1/health"
