---
name: secure-engineering
description: 'Use when implementing or reviewing security-sensitive code, APIs, data flows, dependencies, configuration, permissions, or deployment; assess trust boundaries across components.'
---

# Secure engineering

Apply these checks to the changed behavior and every component it crosses. Follow project-specific security conventions where documented; if security-critical behavior or requirements are unclear, inspect existing code and tests, then ask rather than inventing policy.

## Before changing code

1. Identify assets, entry points, untrusted inputs, sensitive data, privileges, and trust boundaries touched by the task.
2. Trace relevant data and authorization across callers, services, storage, external systems, and outputs. Do not assume that a check at one component protects a different entry point.
3. Inspect existing validation, authentication, authorization, error handling, dependency, and test patterns. Keep the threat analysis proportional to the change.

## Implement and verify

- Validate untrusted input at the receiving boundary with explicit types, limits, and allowlists where appropriate. Use parameterized queries and safe encoding; do not rely on client-side checks.
- Enforce authentication and object/action-level authorization server-side, deny by default, and apply least privilege across processes, credentials, and permissions.
- Protect secrets and sensitive data in storage, transit, logs, errors, and checkpoints. Never add real credentials or environment data to source, tests, examples, or documentation.
- Use safe parsing and serialization; avoid unsafe evaluation, command/path injection, insecure deserialization, and unbounded resource use. Handle failures explicitly without leaking internals or silently weakening security.
- Review dependency provenance, versions, configuration, and lifecycle effects before adding or changing packages. Do not disable existing security controls to make tests pass.
- Add or update focused tests for rejected inputs, unauthorized access, boundary cases, and failures, as relevant. Verify the checks across affected component boundaries.

## Report

Describe the security-relevant behavior changed, tests actually run, and unresolved risks or assumptions. Do not claim a system is secure based only on a passing test or a narrow code review. Escalate confirmed vulnerabilities and high-impact uncertainty clearly.
