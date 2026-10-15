import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Path, Query, status
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout, TooManyRequests
from pydantic import BaseModel, Field, model_validator
from redis import Redis
from redis.exceptions import RedisError


def _postgres_conninfo() -> str:
    return make_conninfo(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def _pool_settings() -> tuple[int, int, float, int]:
    min_size = int(os.environ.get("POSTGRES_POOL_MIN_SIZE", "1"))
    max_size = int(os.environ.get("POSTGRES_POOL_MAX_SIZE", "4"))
    timeout = float(os.environ.get("POSTGRES_POOL_TIMEOUT_SECONDS", "3"))
    max_waiting = int(os.environ.get("POSTGRES_POOL_MAX_WAITING", "32"))
    if min_size < 1 or max_size < min_size:
        raise ValueError("Postgres pool sizes must be positive and ordered")
    if timeout <= 0 or max_waiting < 0:
        raise ValueError("Postgres pool timeout and queue size must be valid")
    return min_size, max_size, timeout, max_waiting


def _build_postgres_pool() -> ConnectionPool:
    min_size, max_size, timeout, max_waiting = _pool_settings()
    return ConnectionPool(
        conninfo=_postgres_conninfo(),
        kwargs={"connect_timeout": 3, "row_factory": dict_row},
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        max_waiting=max_waiting,
        max_idle=300,
        max_lifetime=1_800,
        num_workers=1,
        open=False,
    )


@asynccontextmanager
async def lifespan(application: FastAPI):
    pool = _build_postgres_pool()
    try:
        pool.open(wait=True, timeout=pool.timeout)
        application.state.postgres_pool = pool
        yield
    finally:
        pool.close()


app = FastAPI(title="System Auditor", lifespan=lifespan)


class OrderLineCreate(BaseModel):
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10_000)


class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)
    items: list[OrderLineCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def item_ids_are_unique(self) -> "OrderCreate":
        item_ids = [line.item_id for line in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("items must not contain duplicate item_id values")
        return self


class OrderItemResponse(BaseModel):
    item_id: int
    sku: str
    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderSummaryResponse(BaseModel):
    id: int
    user_id: int
    status: Literal["pending", "paid", "shipped", "cancelled"]
    ordered_at: datetime
    total_cents: int


class OrderResponse(OrderSummaryResponse):
    items: list[OrderItemResponse]


def _postgres_connection():
    return app.state.postgres_pool.connection()


def _check_postgres() -> bool:
    try:
        with _postgres_connection() as connection:
            return connection.execute("SELECT 1 AS status").fetchone()["status"] == 1
    except (
        AttributeError,
        KeyError,
        PoolTimeout,
        TooManyRequests,
        ValueError,
        psycopg.Error,
    ):
        return False


def _check_redis() -> bool:
    try:
        with Redis(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"]),
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as connection:
            return connection.ping()
    except (KeyError, ValueError, RedisError):
        return False


def _check_services() -> dict[str, bool]:
    return {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
    }


def _service_response() -> dict[str, str]:
    services = _check_services()
    response = {
        name: "ok" if is_available else "unavailable"
        for name, is_available in services.items()
    }
    if not all(services.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "services": response},
        )
    return response


def _order_from_connection(
    connection: psycopg.Connection, order_id: int
) -> OrderResponse | None:
    order = connection.execute(
        """
        SELECT id, user_id, status, ordered_at, total_cents
        FROM orders
        WHERE id = %s
        """,
        (order_id,),
    ).fetchone()
    if order is None:
        return None

    items = connection.execute(
        """
        SELECT
            order_items.item_id,
            items.sku,
            items.name,
            order_items.quantity,
            order_items.unit_price_cents,
            order_items.line_total_cents
        FROM order_items
        JOIN items ON items.id = order_items.item_id
        WHERE order_items.order_id = %s
        ORDER BY order_items.item_id
        """,
        (order_id,),
    ).fetchall()
    return OrderResponse(**order, items=items)


def _get_order(order_id: int) -> OrderResponse | None:
    with _postgres_connection() as connection:
        return _order_from_connection(connection, order_id)


def _list_user_orders(
    user_id: int, limit: int, offset: int
) -> list[OrderSummaryResponse] | None:
    with _postgres_connection() as connection:
        user = connection.execute(
            "SELECT 1 FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        if user is None:
            return None

        orders = connection.execute(
            """
            SELECT id, user_id, status, ordered_at, total_cents
            FROM orders
            WHERE user_id = %s
            ORDER BY ordered_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        ).fetchall()
    return [OrderSummaryResponse(**order) for order in orders]


def _create_order(payload: OrderCreate) -> OrderResponse | None:
    with _postgres_connection() as connection, connection.transaction():
        user = connection.execute(
            "SELECT 1 FROM users WHERE id = %s", (payload.user_id,)
        ).fetchone()
        if user is None:
            return None

        item_ids = [line.item_id for line in payload.items]
        items = connection.execute(
            """
            SELECT id, unit_price_cents
            FROM items
            WHERE id = ANY(%s) AND active = true
            """,
            (item_ids,),
        ).fetchall()
        if len(items) != len(payload.items):
            return None

        item_prices = {item["id"]: item["unit_price_cents"] for item in items}
        total_cents = sum(
            item_prices[line.item_id] * line.quantity for line in payload.items
        )
        order = connection.execute(
            """
            INSERT INTO orders (user_id, status, ordered_at, total_cents)
            VALUES (%s, 'pending', now(), %s)
            RETURNING id
            """,
            (payload.user_id, total_cents),
        ).fetchone()

        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO order_items (order_id, item_id, quantity, unit_price_cents)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (
                        order["id"],
                        line.item_id,
                        line.quantity,
                        item_prices[line.item_id],
                    )
                    for line in payload.items
                ],
            )

        return _order_from_connection(connection, order["id"])


def _database_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Database unavailable")


@app.get("/hello")
def hello() -> dict[str, object]:
    services = _service_response()
    return {"message": "Hello, world!", "services": services}


@app.get("/health")
def health() -> dict[str, object]:
    services = _service_response()
    return {"status": "ok", "services": services}


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int = Path(gt=0)) -> OrderResponse:
    try:
        order = _get_order(order_id)
    except (KeyError, PoolTimeout, TooManyRequests, ValueError, psycopg.Error) as error:
        raise _database_unavailable() from error
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/users/{user_id}/orders", response_model=list[OrderSummaryResponse])
def list_orders_for_user(
    user_id: int = Path(gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[OrderSummaryResponse]:
    try:
        orders = _list_user_orders(user_id, limit, offset)
    except (KeyError, PoolTimeout, TooManyRequests, ValueError, psycopg.Error) as error:
        raise _database_unavailable() from error
    if orders is None:
        raise HTTPException(status_code=404, detail="User not found")
    return orders


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate) -> OrderResponse:
    try:
        order = _create_order(payload)
    except (KeyError, PoolTimeout, TooManyRequests, ValueError, psycopg.Error) as error:
        raise _database_unavailable() from error
    if order is None:
        raise HTTPException(
            status_code=404, detail="User or one or more active items not found"
        )
    return order
