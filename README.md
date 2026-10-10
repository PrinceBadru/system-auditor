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
python -m unittest discover -s tests -v
```

### Run the development stack

Requires Docker with the Compose plugin. Copy `.env.example` to `.env`, replace
the placeholder `POSTGRES_PASSWORD` with a local development password, then run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

The API is available at `http://localhost:8000/hello`; application health is at
`http://localhost:8000/health`. Postgres 15 and Redis 7 are also started with
healthchecks, but the hello endpoints do not yet use them. Published ports bind
to localhost. The Compose file limits API resources to 0.5 CPU/512 MiB, Postgres
to 1 CPU/1 GiB, and Redis to 0.5 CPU/256 MiB. Remove the stack with
`docker compose down`; the Postgres named volume is preserved.

GitHub Actions runs Ruff lint and format checks plus the unit tests on Python
3.11, 3.12, and 3.13.

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
