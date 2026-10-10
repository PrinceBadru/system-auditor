# ADR-001: Project scope

## Status

Accepted — 2026-10-11

## Context

The project is named **System Auditor** (`system-auditor`) and is intended to
examine systems and infrastructure. The current repository is an early FastAPI
scaffold; it does not yet implement audit checks or produce audit reports.
Without an explicit boundary, the project name could be mistaken for a tool
that automatically changes or cleans the systems it examines.

## Decision

System Auditor's scope is to assess systems and infrastructure, identify
potential issues and improvement opportunities, and communicate findings that
are relevant to the examined environment. The product is read-only by default:
automated remediation, cleanup, or other changes to audited environments are
out of scope unless a future decision explicitly adds them.

Supported environments, audit checks, integrations, authentication and
authorization requirements, and report formats remain undecided. They must be
specified before implementation implies support for them.

## Consequences

- Product behavior and documentation should distinguish analysis from
  remediation.
- Audit results should be contextualized to the environment actually examined.
- The current scaffold is not evidence that any audit capability or target
  environment is supported.
- Future scope expansions, especially actions that modify audited systems,
  require an explicit decision and security review.
