# Project context

Compact, repository-backed facts for agents starting in a fresh task or environment. Keep this file factual and update it when durable project understanding changes; use ADRs for decisions and `docs/AGENT_STATE.md` only for active work.

## Verified project facts

- **Name:** System Auditor (`system-auditor`).
- **Purpose:** Examine systems and infrastructure, identify potential issues and improvement opportunities, and communicate environment-specific findings.
- **Stage:** Early FastAPI scaffold with hello and dependency-readiness endpoints; audit capabilities are not implemented.
- **Python:** Requires Python 3.11 or newer; GitHub Actions runs Ruff checks on Python 3.12. See [ADR 0002](adr/0002-python.md).
- **Development services:** Docker Compose provides FastAPI connected to Postgres 15 and Redis 7; all services have resource limits and healthchecks.
- **Order seed data:** `scripts/db/schema.sql` defines a relational users/orders/items schema with `order_items`; `scripts/db/seed_orders.py` applies it and seeds 100,000 synthetic orders by default.
- **Order API:** FastAPI exposes unauthenticated endpoints to retrieve an order, list a user's orders with bounded pagination, and create pending orders using active catalog items. See `src/system_auditor/main.py`.
- **API runtime:** The Compose API service is limited to 0.5 CPU and 512 MiB. It runs one Uvicorn worker with a bounded concurrency of 32 and uses a Postgres pool of one to four connections with one pool worker.
- **Benchmark baseline:** Local k6 `/hello` smoke runs, five-run repeatability results, and one Azure Retail Prices API probe are recorded in [docs/environment.md](environment.md); raw k6 JSON is in `artifacts/k6/`. [The five-rate sweep runner](../scripts/k6/run_baseline_sweep.py) captures per-rate latency, errors, and Compose CPU/memory; sweep measurements have not yet been recorded.
- **Unknown by design:** Supported environments, checks, report formats, implementation architecture, and runtime behavior have not yet been defined in the project records.

## Context map

- [Canonical cross-agent instructions](../AGENTS.md) — shared project workflow and links to task-specific procedures.
- [Gemini entry point](../GEMINI.md) — imports the canonical instructions.
- [Claude entry point](../CLAUDE.md) — imports the canonical instructions.
- [Copilot entry point](../.github/copilot-instructions.md) — points to the canonical instructions.
- [README](../README.md) — project purpose, status, and intended direction.
- [ADR index](adr/README.md) — architecture decisions; read relevant records before changing a recorded decision.
- [Project scope](adr/0001-project-name-and-scope.md) and [repeatable-run criteria](adr/0003-repeatable-run.md) — scope boundary and measurement protocol.
- [Agent checkpoint](AGENT_STATE.md) — current multi-step task recovery state, if active.
- [Project continuity skill](../.github/skills/project-continuity/SKILL.md) — startup, checkpoint, and handoff procedure.
- [Secure engineering skill](../.github/skills/secure-engineering/SKILL.md) — security workflow for changes crossing components or trust boundaries.

## Working constraints

- Distinguish intended direction from implemented and verified behavior.
- Record durable architectural choices as ADRs; do not infer an architecture from the project name.
- Determine supported environments and available validation commands from the repository as it evolves; do not assume a local toolchain exists in another environment.
