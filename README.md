# System Auditor

System Auditor is a project for examining systems and infrastructure, identifying
opportunities for improvement, and presenting useful, environment-specific
insights.

## Project status

This repository currently contains a minimal FastAPI scaffold, a `/hello`
endpoint, and health checks for the application and supporting containers.
Auditing capabilities are not implemented yet.

## Development

Requires Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
```

### Run the development stack

Requires Docker with the Compose plugin. Copy `.env.example` to `.env`, replace
the placeholder `POSTGRES_PASSWORD` with a local development password, then run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

The API is available at `http://localhost:8000/hello`; application readiness is
at `http://localhost:8000/health`. Both endpoints check Postgres 15 with a
database query and Redis 7 with `PING`; they report HTTP 503 if either
dependency is unavailable. The API connects to the Compose service names over
the private Compose network. Only the API is published to localhost; Postgres
and Redis are reachable only inside the Compose network. The Compose file
limits API resources to 0.5 CPU/512 MiB, Postgres to 1 CPU/1 GiB, and Redis to
0.5 CPU/256 MiB. Remove the stack with `docker compose down`; the Postgres named
volume is preserved.

GitHub Actions runs Ruff lint and format checks on Python 3.12.

### Run the k6 hello smoke test

Install k6 with winget, start the Compose stack as described above, then run
from the repository root:

```powershell
winget install --id GrafanaLabs.k6 --exact
New-Item -ItemType Directory -Force artifacts\k6
k6 run --out json=artifacts/k6/hello-first-run.json scripts/k6/hello.js
k6 run --out json=artifacts/k6/hello-ramp-first-run.json scripts/k6/hello-ramp.js
k6 run --out json=artifacts/k6/hello-models.json scripts/k6/hello-models.js
```

The first smoke run and multi-VU ramp results are recorded in
[docs/environment.md](docs/environment.md).

The models run sequentially: a 30-second open-model constant arrival rate of
10 iterations per second, followed by a 30-second closed-model scenario with
4 fixed virtual users. The open-model scenario allows up to 10 VUs and fails
the run if k6 drops any scheduled iterations.

### Run the five-rate baseline sweep

With the Compose stack running and healthy, set `POSTGRES_PASSWORD` as
described above and run from the repository root:

```powershell
python scripts/k6/run_baseline_sweep.py
```

The sweep runs sequential 30-second open-model stages at 5, 10, 15, 20, and
25 iterations per second, with a five-second cooldown between stages. It records
k6 p50/p95/p99 latency, HTTP and check failures, and dropped iterations for
each rate. While each stage runs, it samples API, Postgres, and Redis container
CPU and memory approximately once per second.

Each run writes to a new timestamped directory under `artifacts/k6/`. The
`baseline-summary.csv` and `.json` files contain per-rate results; the
`resource-samples.csv` file has timestamped raw container samples. Raw k6
metrics, k6 summaries, and process logs are kept alongside them. Resource
averages and maxima are calculated from the samples collected during each
rate's active stage.

### Create and seed the order schema

The relational order schema is defined in
[`scripts/db/schema.sql`](scripts/db/schema.sql). It creates `users`, `items`,
`orders`, and `order_items`, with foreign keys from orders to users and order
lines to both orders and items.

With the Compose stack running and `POSTGRES_PASSWORD` set in your shell, seed
100,000 synthetic orders:

```powershell
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "system_auditor"
$env:POSTGRES_USER = "system_auditor"
$env:POSTGRES_PASSWORD = "replace-with-your-local-development-password"
python scripts/db/seed_orders.py --reset
```

The seed command defaults to 10,000 users, 1,000 items, and 100,000 orders. Use
`--orders`, `--users`, or `--items` to change those counts.

### Order API

After applying the schema and seeding data, the API provides:

- `GET /orders/{order_id}` to retrieve an order and its line items.
- `GET /users/{user_id}/orders?limit=50&offset=0` to retrieve a user's orders.
- `POST /orders` to create a pending order from existing active items.

Create requests accept a `user_id` and one to 100 unique item lines:

```json
{
  "user_id": 1,
  "items": [{"item_id": 1, "quantity": 2}]
}
```

### API runtime limits

The Compose API service is capped at 0.5 CPU and 512 MiB, which is below the
requested one CPU ceiling. It runs one Uvicorn worker with a concurrency limit
of 32, a five-second keep-alive timeout, and a 30-second graceful shutdown
window.

Each API worker owns one Postgres connection pool. The Compose defaults keep
one ready connection, allow at most four connections, and cap the waiting queue
at 32 requests. Adjust `POSTGRES_POOL_MIN_SIZE`, `POSTGRES_POOL_MAX_SIZE`,
`POSTGRES_POOL_TIMEOUT_SECONDS`, or `POSTGRES_POOL_MAX_WAITING` only after
accounting for the available database connection budget.

## Intended direction

The project aims to help people understand the systems they operate by:

- examining an environment and its configuration;
- highlighting potential issues and improvement opportunities; and
- producing clear findings relevant to the environment that was examined.

The exact supported environments, audit checks, and report formats will be
defined as the project develops.

## Architecture decisions

The reasoning behind significant project choices is recorded in
[docs/adr](docs/adr/README.md).

## License

This project is licensed under the [MIT License](LICENSE).
