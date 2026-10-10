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
```

The first smoke run and multi-VU ramp results are recorded in
[docs/environment.md](docs/environment.md).

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
