import os

import psycopg
from fastapi import FastAPI, HTTPException
from redis import Redis
from redis.exceptions import RedisError

app = FastAPI(title="System Auditor")


def _check_postgres() -> bool:
    try:
        with psycopg.connect(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ["POSTGRES_PORT"]),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=3,
        ) as connection:
            return connection.execute("SELECT 1").fetchone() == (1,)
    except (KeyError, ValueError, psycopg.Error):
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


@app.get("/hello")
def hello() -> dict[str, object]:
    services = _service_response()
    return {"message": "Hello, world!", "services": services}


@app.get("/health")
def health() -> dict[str, object]:
    services = _service_response()
    return {"status": "ok", "services": services}
