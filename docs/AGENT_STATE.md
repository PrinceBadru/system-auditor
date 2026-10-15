# Agent work checkpoint

This file is a compact recovery point for one active, multi-step task. Keep it free of secrets, personal data, source-code copies, and large logs. If there is no active task, leave only this instruction.

## Active task

- **Status:** Implementation complete; final validation in progress.
- **Goal:** Reuse Postgres connections, configure the API worker runtime, and ensure the API stays below 1 CPU and 512 MiB.
- **Scope and decisions:** Keep the existing API limit of 0.5 CPU and 512 MiB. Use one Uvicorn worker with bounded concurrency and a per-worker pool sized from one to four connections. Pool settings are environment-configurable and validated at startup; connection configuration remains sourced from the existing Postgres environment variables.
- **Changed files:** `pyproject.toml`, `Dockerfile`, `compose.yaml`, `src/system_auditor/main.py`, `tests/test_order_api.py`, `README.md`, and `docs/PROJECT_CONTEXT.md`.
- **Validation:** Verified the installed pool API supports the configured startup timeout. A Compose validation without `POSTGRES_PASSWORD` correctly stopped at its required-secret check; full checks remain.
- **Next action:** Run unit, lint, format, compile, and Compose validation with a non-secret placeholder; clear this checkpoint if they pass.
