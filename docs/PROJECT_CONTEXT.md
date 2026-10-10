# Project context

Compact, repository-backed facts for agents starting in a fresh task or environment. Keep this file factual and update it when durable project understanding changes; use ADRs for decisions and `docs/AGENT_STATE.md` only for active work.

## Verified project facts

- **Name:** System Auditor (`system-auditor`).
- **Purpose:** Examine systems and infrastructure, identify potential issues and improvement opportunities, and communicate environment-specific findings.
- **Stage:** Early FastAPI scaffold with hello and health endpoints; audit capabilities are not implemented.
- **Python:** Requires Python 3.11 or newer; GitHub Actions tests Python 3.11, 3.12, and 3.13.
- **Development services:** Docker Compose provides FastAPI, Postgres 15, and Redis 7 with resource limits and healthchecks.
- **Unknown by design:** Supported environments, checks, report formats, implementation architecture, and runtime behavior have not yet been defined in the project records.

## Context map

- [Canonical cross-agent instructions](../AGENTS.md) — shared project workflow and links to task-specific procedures.
- [Gemini entry point](../GEMINI.md) — imports the canonical instructions.
- [Claude entry point](../CLAUDE.md) — imports the canonical instructions.
- [Copilot entry point](../.github/copilot-instructions.md) — points to the canonical instructions.
- [README](../README.md) — project purpose, status, and intended direction.
- [ADR index](adr/README.md) — architecture decisions; read relevant records before changing a recorded decision.
- [Agent checkpoint](AGENT_STATE.md) — current multi-step task recovery state, if active.
- [Project continuity skill](../.github/skills/project-continuity/SKILL.md) — startup, checkpoint, and handoff procedure.
- [Secure engineering skill](../.github/skills/secure-engineering/SKILL.md) — security workflow for changes crossing components or trust boundaries.

## Working constraints

- Distinguish intended direction from implemented and verified behavior.
- Record durable architectural choices as ADRs; do not infer an architecture from the project name.
- Determine supported environments and available validation commands from the repository as it evolves; do not assume a local toolchain exists in another environment.
