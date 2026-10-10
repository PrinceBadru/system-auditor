# Project agent instructions

This is the canonical, tool-neutral instruction entry point for agents working in this repository. Native entry points for other agents should import or point here rather than duplicate project policy.

## Every task

- Read [project context](docs/PROJECT_CONTEXT.md) first; load only the files needed. Do not assume features, supported platforms, or architecture that are not implemented or recorded.
- Inspect repository status before editing. Preserve user changes; never overwrite, discard, or stage unrelated work.
- Follow existing project patterns. Use the smallest relevant tests, lint, and build commands; add or update tests and directly related documentation, and report commands and results accurately.
- Keep durable facts and decisions in `docs/PROJECT_CONTEXT.md` and ADRs, not chat-only memory. Never store secrets, personal data, or sensitive environment details in context files.
- Do not commit, push, or publish unless the user asks.

## Load when relevant

- For multi-step, resumable, or handoff work, follow the [project-continuity procedure](.github/skills/project-continuity/SKILL.md) and maintain [the task checkpoint](docs/AGENT_STATE.md).
- For code, dependencies, APIs, data flows, permissions, or deployment that touch security boundaries, follow the [secure-engineering procedure](.github/skills/secure-engineering/SKILL.md).

## Context portability

The repository is the durable source of truth. A local, uncommitted checkpoint is available only in that working tree; recovery in a fresh clone or another environment requires the relevant changes to be committed and shared. Never commit or publish without authorization.
