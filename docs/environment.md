# Benchmark environment

This document records the local environment used for the first k6 smoke-load
run. Results are specific to this machine and configuration; they are not
production capacity claims.

## Machine

- **Operating system:** Microsoft Windows 11 Pro, version 10.0.22621, 64-bit.
- **CPU:** Intel Core i5-6300U @ 2.40 GHz; 2 cores, 4 logical processors.
- **Physical RAM:** 8,450,605,056 bytes (7.87 GiB).
- **Power mode:** Windows Balanced power plan. Whether the machine was on AC
  power during the run was not recorded.
- **Docker:** Docker Engine 29.8.2, Docker Compose 5.5.1.

## Services and load

- **k6:** Grafana k6 v2.2.0, installed with winget (`GrafanaLabs.k6`).
- **Target:** FastAPI `/hello` on `http://127.0.0.1:8000/hello`.
- **Dependencies:** Postgres 15 and Redis 7 in a dedicated Docker Compose
  project; each request checks both dependencies.
- **Container limits:** API 0.5 CPU/512 MiB, Postgres 1 CPU/1 GiB, Redis 0.5
  CPU/256 MiB.
- **k6 profile:** 1 virtual user for 10 seconds; verifies HTTP 200 and healthy
  Postgres and Redis indicators on every response.
- **Raw output:** [hello-first-run.json](../artifacts/k6/hello-first-run.json).

## First run

Run date: 2026-10-10 (local machine date).

- **Requests:** 247 completed over 10 seconds (24.65 requests/second).
- **HTTP failures:** 0%; all 247 requests returned successfully.
- **Checks:** 741/741 passed, including HTTP status and both dependency
  indicators.
- **Response time:** 40.21 ms average, 34.12 ms median, 73.23 ms p95, 114 ms
  maximum.
- **Raw JSON:** 943,998 bytes of newline-delimited k6 metric records. Initial
  metadata samples in the raw file do not contain metric values; aggregate
  counts above match the k6 end-of-run summary.

This is a short, single-machine smoke-load baseline. It is not a capacity,
scaling, or production-readiness test.
