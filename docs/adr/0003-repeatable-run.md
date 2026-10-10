# ADR-003: Repeatable run

## Status

Accepted — 2026-10-11

## Context

Performance and external-service observations are useful only when their
procedure and environment are clear. Identical inputs do not guarantee
identical timings, particularly on a shared development machine or when the
upstream data is live.

## Decision

A run is repeatable for comparison when its executable procedure is held
constant and its conditions are recorded. At minimum, record:

- repository revision and exact script or request, including parameters;
- target and dependency versions/configuration, including resource limits;
- runtime/tool version and host operating system, CPU/RAM, and power mode;
- run date/time, warm-up/readiness procedure, and any known concurrent load;
- raw output and per-run success and performance metrics.

For a performance comparison, execute five sequential repetitions of the same
profile against the same warmed deployment without changing configuration
between repetitions. Keep each repetition's raw output, report per-run
statistics, the observed min-to-max spread, and the coefficient of variation
(CV) for key run-level metrics; report failures explicitly. Calculate CV as the
sample standard deviation divided by the sample mean, expressed as a
percentage. Report CV separately for each metric and do not interpret it alone
as proof of acceptable performance. Treat this five-run set as a local
comparison, not a capacity guarantee. Do not pool samples across repetitions
in a way that hides run-to-run variation.

For a live external API, repeatability means replaying the same versioned
endpoint and query and recording the request timestamp, response status,
elapsed time, and response shape. Returned prices or other live values may
change; equal response values are not a repeatability requirement.

## Consequences

- Results can be traced to a procedure and compared without implying that the
  environment was perfectly controlled.
- Run-to-run variability is quantified with a consistent sample-CV definition;
  the metric and sample size must accompany each reported CV.
- Materially different host load, configuration, dependencies, or request
  parameters require a separate result set.
- Short or variable runs must be reported as exploratory evidence, with
  limitations stated.
