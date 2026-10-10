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

## Multi-VU latency run

Run date: 2026-10-11 (local machine date).

- **Profile:** Sequential 30-second constant-VU scenarios at 1, 2, and 4 VUs,
  with 5-second gaps between scenarios.
- **Raw output:** [hello-ramp-first-run.json](../artifacts/k6/hello-ramp-first-run.json).
- **Power state:** Windows reported AC power before the run; the two battery
  devices reported 79% and 70% charge.
- **Failures:** 0 HTTP failures; all 5,388 checks passed (HTTP status plus
  Postgres and Redis health for each request).

| Scenario | Requests | Throughput | Median | p90 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 VU | 773 | 25.77 req/s | 31.81 ms | 57.59 ms | 66.45 ms | 96.83 ms | 192.69 ms |
| 2 VUs | 541 | 18.03 req/s | 97.28 ms | 191.12 ms | 204.69 ms | 286.97 ms | 311.37 ms |
| 4 VUs | 482 | 16.07 req/s | 215.06 ms | 378.38 ms | 397.99 ms | 478.67 ms | 503.00 ms |

Percentiles are calculated from each scenario's raw `http_req_duration` points
using linear interpolation between sorted samples. Throughput is request count
divided by the 30-second scenario duration.

### Findings

- No functional failures occurred, and all requests returned HTTP 200 with
  healthy dependency indicators.
- Latency degraded substantially under concurrency: p95 rose from 66.45 ms at
  1 VU to 397.99 ms at 4 VUs (about 6x).
- Throughput also fell, from 25.77 req/s at 1 VU to 16.07 req/s at 4 VUs. This
  indicates a performance/scaling concern in this local configuration, even
  though requests continued to succeed.
- A likely contributor is that each request opens a fresh Postgres connection
  and Redis client in the API rather than reusing pooled clients. The API's
  0.5-CPU container limit and Docker Desktop overhead may also contribute; this
  run did not collect resource or connection telemetry, so the cause is not
  established.
- No latency threshold was configured. k6's passing thresholds establish
  functional success only, not acceptable performance.

The fixed 30-second stages provide a more useful comparison than the original
10-second smoke test, but still do not establish production capacity.

### Diagnostic repeat

Run date: 2026-10-11 (local machine date). This repeated the same 1/2/4-VU
profile in a fresh Compose project while sampling container CPU/memory and
Postgres backend count approximately every 5 seconds. The raw measurements are
in [hello-ramp-diagnostic.json](../artifacts/k6/hello-ramp-diagnostic.json) and
[hello-ramp-diagnostic-resources.csv](../artifacts/k6/hello-ramp-diagnostic-resources.csv).

| Scenario | Requests | Throughput | Median | p90 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 VU | 629 | 20.97 req/s | 39.01 ms | 75.45 ms | 98.21 ms | 157.10 ms | 243.26 ms |
| 2 VUs | 516 | 17.20 req/s | 98.01 ms | 193.63 ms | 214.19 ms | 384.31 ms | 766.11 ms |
| 4 VUs | 431 | 14.37 req/s | 274.57 ms | 420.10 ms | 494.92 ms | 597.90 ms | 792.72 ms |

- All 1,576 requests returned HTTP 200; all 4,728 endpoint/dependency checks
  passed.
- The same concurrency trend appeared again. Compared with the earlier ramp
  run, p95 was higher by approximately 48% at 1 VU, 5% at 2 VUs, and 24% at
  4 VUs. Both runs therefore show degradation with concurrency, but their
  absolute latency differs materially.
- During this repeat, sampled API CPU averaged 43.6%, 47.5%, and 51.9% at 1, 2,
  and 4 VUs respectively, peaking at 60.7%. Postgres averaged 34-40% CPU and
  peaked around 71%; Redis averaged 2-5%. API memory peaked at approximately
  57 MiB of its 512 MiB limit; Postgres and Redis memory also remained far
  below their limits.
- The host CPU load was already 76% before this diagnostic repeat. This
  contributes uncertainty to comparisons between runs.
- Postgres backend samples saw at most two sessions (the application plus the
  sampler at those instants). Sampling every few seconds is too coarse to
  observe short-lived connection churn.

**Conclusion:** The load-related latency/throughput degradation is repeatable
in this local setup. API and Postgres CPU activity are consistent with CPU
pressure; memory pressure is not indicated. The measurements do **not** prove
that fresh database/Redis connections are the cause, nor isolate connection
setup cost from host contention, application CPU, or Docker scheduling. Confirm
that hypothesis with a controlled A/B run using pooled/reused clients and
resource/connection telemetry captured under comparable host load.

## Five-run smoke-test repeat

Run date: 2026-10-11 (local machine date). The unchanged
[`scripts/k6/hello.js`](../scripts/k6/hello.js) smoke test was run five times
sequentially against one isolated Compose deployment. Each run used k6 v2.2.0,
one virtual user for 10 seconds, and the same HTTP 200, Postgres, and Redis
checks. Readiness was confirmed before the first run; services were not
restarted between repetitions. The Compose project used the documented
per-service CPU/memory limits. Windows reported the Balanced power plan; battery
telemetry and host CPU load were unavailable, so AC status and other host load
are unknown. The repository revision was `f08ea6e`.

| Run | Requests | Throughput | Median | p95 | Maximum | HTTP/check failures |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 144 | 14.25 req/s | 56.64 ms | 118.22 ms | 517.70 ms | 0 / 0 |
| 2 | 121 | 11.98 req/s | 46.02 ms | 269.18 ms | 506.43 ms | 0 / 0 |
| 3 | 195 | 19.43 req/s | 47.25 ms | 86.04 ms | 215.88 ms | 0 / 0 |
| 4 | 172 | 16.97 req/s | 46.57 ms | 95.63 ms | 759.65 ms | 0 / 0 |
| 5 | 131 | 13.03 req/s | 48.55 ms | 145.45 ms | 1,975.00 ms | 0 / 0 |

Across all five runs, 763 requests succeeded and all 2,289 endpoint/dependency
checks passed. Throughput ranged from 11.98 to 19.43 req/s. Median latency
ranged from 46.02 to 56.64 ms, while p95 ranged from 86.04 to 269.18 ms
(approximately 3.1x); the slowest individual request was 1.975 seconds.
Latency percentiles are calculated from each run's raw `http_req_duration`
samples with linear interpolation. The substantial p95 and throughput spread,
including one long-tail outlier, means the prior single-run baseline is not a
stable performance estimate. Functional success was consistent, but these
short runs do not identify why timings varied; host load and power-source state
were not controlled or captured.

For the five run-level observations, sample CV is sample standard deviation
divided by sample mean, expressed as a percentage:

| Metric | Mean | Sample standard deviation | Sample CV |
|---|---:|---:|---:|
| Throughput | 15.13 req/s | 3.04 req/s | 20.08% |
| Median latency | 49.01 ms | 4.37 ms | 8.92% |
| p95 latency | 142.90 ms | 74.21 ms | 51.93% |

The high p95 CV reflects substantial tail-latency variation across these five
short runs. CV is descriptive, not an acceptance threshold or a cause analysis;
the sample is small and host conditions were not controlled.

Raw outputs, one file per repetition:

- [Run 1](../artifacts/k6/hello-repeat-run-01.json)
- [Run 2](../artifacts/k6/hello-repeat-run-02.json)
- [Run 3](../artifacts/k6/hello-repeat-run-03.json)
- [Run 4](../artifacts/k6/hello-repeat-run-04.json)
- [Run 5](../artifacts/k6/hello-repeat-run-05.json)

## Azure Retail Prices API probe

On 2026-10-11 at 01:35 (+03:00), one unauthenticated HTTPS GET was sent
directly to the public Azure Retail Prices API. The OData filter was
`serviceName eq 'Virtual Machines' and armRegionName eq 'eastus' and priceType eq 'Consumption'`.
The API returned HTTP 200 in 3,379.4 ms. The response's first page contained
1,000 items and a next-page link, so this was a connectivity and response-shape
check, not a complete price inventory.

The first returned item was `Virtual Machines NCdsxlRTX6kv6 Windows`, SKU
`NC320dsxlRTX6Kv6 Spot`, ARM SKU
`Standard_NC320ds_xl_RTXPRO6000BSE_v6`, in `eastus`; its returned retail price
was 5.785718 USD per hour, effective 2026-08-01. This is one live API record,
not a pricing recommendation or a quote for an account. Microsoft documents
the public API as unauthenticated in the
[Azure Retail Prices REST API overview](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices).
No credentials were used. No application integration was added or tested.
