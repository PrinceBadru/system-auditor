---
name: project-continuity
description: 'Use when starting, resuming, or handing off multi-step project work; recover context after a new task, environment change, or interruption using compact repository records.'
---

# Project continuity

Use repository files—not chat history—as the source of truth. Keep routine context reads small and load detail progressively.

## Start or resume work

1. Read `docs/PROJECT_CONTEXT.md` and inspect repository status before editing. Read `docs/AGENT_STATE.md` if it records an active task.
2. If a checkpoint exists, compare its task, decisions, changed files, and next step with the current request and working tree. Resume only compatible work; preserve unrelated edits. If the request differs, do not silently replace an active checkpoint—finish, clearly supersede, or ask the user.
3. Read the README, relevant ADRs, and source/test files only as needed. Search for existing patterns before introducing new ones. Confirm the applicable environment and commands from repository files rather than assuming tools or paths.
4. For multi-step or interruption-prone work, write a concise checkpoint to `docs/AGENT_STATE.md` before implementation. Keep it updated after meaningful milestones and before lengthy or risky operations.

## Checkpoint contents

Record only actionable recovery information:

- task and status;
- goal, scope, and important decisions or constraints;
- files changed and relevant uncommitted user changes;
- commands run and exact validation results;
- the single safest next action, plus blockers.

Do not copy source code, credentials, tokens, personal data, or large logs into the checkpoint. Link to files and summarize. Never claim an operation or test succeeded unless its result was observed.

## Finish or hand off

- Verify the requested behavior with the narrowest relevant tests, lint, and build checks; record results and any limitations.
- On completion, clear the active checkpoint and retain only genuinely durable project facts or decisions in `docs/PROJECT_CONTEXT.md` or a new ADR.
- On interruption or handoff, leave status, current state, validation, and the next safe action explicit.
- A local checkpoint helps recovery only where its working tree is available. A new clone or environment can recover only repository state that was committed and shared. Do not commit or publish without authorization; tell the user when sharing is needed.
