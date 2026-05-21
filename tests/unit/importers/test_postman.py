"""Postman Collection 导入器单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mwjrunner.importers import import_postman_collection

SAMPLE_COLLECTION = {
    "info": {
        "name": "Test API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [
        {
            "name": "Get Users",
            "request": {
                "method": "GET",
                "url": {"raw": "http://localhost:8000/api/users", "host": ["localhost"], "path": ["api", "users"]},
                "header": [{"key": "Accept", "value": "application/json"}],
            },
        },
        {
            "name": "Create User",
            "request": {
                "method": "POST",
                "url": "http://localhost:8000/api/users",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": '{"name": "test", "email": "test@example.com"}',
                    "options": {"raw": {"language": "json"}},
                },
            },
        },
        {
            "name": "Auth Folder",
            "item": [
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "url": "http://localhost:8000/api/login",
                        "body": {
                            "mode": "urlencoded",
                            "urlencoded": [
                                {"key": "username", "value": "admin"},
                                {"key": "password", "value": "secret"},
                            ],
                        },
                    },
                }
            ],
        },
    ],
}


@pytest.mark.unit
class TestPostmanImporter:
    """Postman 导入器测试。"""

    def test_import_generates_yaml_files(self, tmp_path: Path) -> None:
        collection_file = tmp_path / "collection.json"
        collection_file.write_text(json.dumps(SAMPLE_COLLECTION), encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = import_postman_collection(collection_file, output_dir)

        assert len(generated) == 3
        assert (output_dir / "Get_Users.yaml").exists()
        assert (output_dir / "Create_User.yaml").exists()
        assert (output_dir / "Auth_Folder" / "Login.yaml").exists()

    def test_generated_case_structure(self, tmp_path: Path) -> None:
        collection_file = tmp_path / "collection.json"
        collection_file.write_text(json.dumps(SAMPLE_COLLECTION), encoding="utf-8")

        output_dir = tmp_path / "output"
        import_postman_collection(collection_file, output_dir)

        case_data = yaml.safe_load((output_dir / "Get_Users.yaml").read_text(encoding="utf-8"))
        assert case_data["name"] == "Get Users"
        assert case_data["tags"] == ["imported"]
        assert case_data["steps"][0]["request"]["method"] == "GET"
        assert case_data["steps"][0]["request"]["url"] == "http://localhost:8000/api/users"
        assert case_data["steps"][0]["request"]["headers"]["Accept"] == "application/json"

    def test_json_body_parsed(self, tmp_path: Path) -> None:
        collection_file = tmp_path / "collection.json"
        collection_file.write_text(json.dumps(SAMPLE_COLLECTION), encoding="utf-8")

        output_dir = tmp_path / "output"
        import_postman_collection(collection_file, output_dir)

        case_data = yaml.safe_load((output_dir / "Create_User.yaml").read_text(encoding="utf-8"))
        assert case_data["steps"][0]["request"]["json"] == {"name": "test", "email": "test@example.com"}

    def test_urlencoded_body_parsed(self, tmp_path: Path) -> None:
        collection_file = tmp_path / "collection.json"
        collection_file.write_text(json.dumps(SAMPLE_COLLECTION), encoding="utf-8")

        output_dir = tmp_path / "output"
        import_postman_collection(collection_file, output_dir)

        case_data = yaml.safe_load((output_dir / "Auth_Folder" / "Login.yaml").read_text(encoding="utf-8"))
        assert case_data["steps"][0]["request"]["data"] == {"username": "admin", "password": "secret"}

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            import_postman_collection(tmp_path / "nonexistent.json", tmp_path / "output")

    def test_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON 解析失败"):
            import_postman_collection(bad_file, tmp_path / "output")

    def test_default_assertion_added(self, tmp_path: Path) -> None:
        collection_file = tmp_path / "collection.json"
        collection_file.write_text(json.dumps(SAMPLE_COLLECTION), encoding="utf-8")

        output_dir = tmp_path / "output"
        import_postman_collection(collection_file, output_dir)

        case_data = yaml.safe_load((output_dir / "Get_Users.yaml").read_text(encoding="utf-8"))
        assert case_data["steps"][0]["assertions"] == [{"type": "status_code", "expected": 200}]
