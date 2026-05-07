from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_token() -> None:
    response = client.post(
        "/api/login",
        json={"username": "demo", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["token"] == "demo-token"


def test_login_rejects_invalid_password() -> None:
    response = client.post(
        "/api/login",
        json={"username": "demo", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == 40102


def test_profile_requires_token() -> None:
    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == 40101


def test_profile_returns_user_with_token() -> None:
    response = client.get(
        "/api/profile",
        headers={"Authorization": "Bearer demo-token"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "demo"


def test_list_items_filters_by_keyword() -> None:
    response = client.get("/api/items", params={"keyword": "book"})

    assert response.status_code == 200
    assert response.json()["data"] == [{"id": 1, "name": "book", "price": 39.9}]


def test_create_item_requires_token() -> None:
    response = client.post("/api/items", json={"name": "pencil", "price": 3.5})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == 40101


def test_create_item_returns_created_item() -> None:
    response = client.post(
        "/api/items",
        headers={"Authorization": "Bearer demo-token"},
        json={"name": "pencil", "price": 3.5},
    )

    assert response.status_code == 201
    assert response.json()["message"] == "created"
    assert response.json()["data"]["name"] == "pencil"


def test_error_returns_fixed_error() -> None:
    response = client.get("/api/error")

    assert response.status_code == 500
    assert response.json() == {"code": 50001, "message": "示例错误"}
