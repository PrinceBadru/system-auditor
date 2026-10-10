# ADR-002: Python

## Status

Accepted — 2026-10-11

## Context

The initial API scaffold uses FastAPI and declares Python 3.11 as its minimum
version. A primary implementation language is needed for the service and the
first audit capabilities, while keeping the project straightforward to develop
and validate.

## Decision

Use Python 3.11 or newer for the API and initial System Auditor
implementation. Keep the existing FastAPI HTTP layer and use Ruff for linting
and formatting.

## Consequences

- Python is the default implementation language for new application
  functionality.
- Runtime and CI changes must respect the Python 3.11 minimum; CI currently
  validates with Python 3.12.
- New dependencies and platform-specific behavior should be justified and
  validated rather than assumed portable.
- A future component may use another language when its requirements justify
  that choice; record the boundary and integration in a separate decision.
