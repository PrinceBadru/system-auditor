# Project instructions

- Start with [the project context](../docs/PROJECT_CONTEXT.md); load only the files needed for the task. Do not assume features, platforms, or architecture that are not implemented or recorded.
- For multi-step work, use the [project-continuity skill](skills/project-continuity/SKILL.md): record a resumable checkpoint in `docs/AGENT_STATE.md`, refresh it at meaningful milestones, and clear it on completion.
- Follow the [secure-engineering skill](skills/secure-engineering/SKILL.md) when changing or reviewing code, dependencies, data flows, permissions, or deployment. Treat trust boundaries and component interactions as part of the change.
- Inspect repository status before editing. Preserve existing user changes; never overwrite, discard, or stage unrelated work.
- Follow existing project patterns and use the smallest relevant tests, lint, and build commands. Add or update tests and directly related documentation; report commands and outcomes accurately.
- Keep project facts and durable decisions in `docs/PROJECT_CONTEXT.md` and ADRs, not in chat-only memory. Do not store secrets, personal data, or sensitive environment details in context files.
- Do not commit, push, or publish unless the user asks. Uncommitted checkpoints survive only where that working tree is available; cross-environment recovery requires sharing the updated files through the repository.
