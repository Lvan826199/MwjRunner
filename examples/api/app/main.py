from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

app = FastAPI(title="MwjRunner Example API", version="0.1.0")

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "123456"
DEMO_TOKEN = "demo-token"

ITEMS = [
    {"id": 1, "name": "book", "price": 39.9},
    {"id": 2, "name": "pen", "price": 9.9},
    {"id": 3, "name": "bag", "price": 19.9},
]


class LoginRequest(BaseModel):
    username: str
    password: str


class ItemCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


def require_token(authorization: str | None) -> None:
    if authorization != f"Bearer {DEMO_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "unauthorized"},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginRequest) -> dict[str, object]:
    if payload.username != DEMO_USERNAME or payload.password != DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40102, "message": "invalid username or password"},
        )

    return {
        "code": 0,
        "message": "success",
        "data": {"token": DEMO_TOKEN},
    }


@app.get("/api/profile")
def profile(authorization: Annotated[str | None, Header()] = None) -> dict[str, object]:
    require_token(authorization)
    return {
        "code": 0,
        "data": {
            "username": DEMO_USERNAME,
            "nickname": "示例用户",
        },
    }


@app.get("/api/items")
def list_items(keyword: Annotated[str | None, Query()] = None) -> dict[str, object]:
    if keyword:
        filtered_items = [item for item in ITEMS if keyword.lower() in item["name"].lower()]
    else:
        filtered_items = ITEMS

    return {"code": 0, "data": filtered_items}


@app.post("/api/items", status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    require_token(authorization)
    return {
        "code": 0,
        "message": "created",
        "data": {
            "id": max(item["id"] for item in ITEMS) + 1,
            "name": payload.name,
            "price": payload.price,
        },
    }


@app.get("/api/error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
def example_error() -> dict[str, object]:
    return {"code": 50001, "message": "示例错误"}
