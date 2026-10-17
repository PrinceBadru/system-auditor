import tempfile
from pathlib import Path
from unittest import TestCase

from scripts.k6.run_baseline_sweep import (
    parse_memory_usage,
    percentile,
    read_k6_metrics,
    resource_summary,
)


class BaselineSweepTests(TestCase):
    def test_percentile_uses_linear_interpolation(self) -> None:
        self.assertEqual(percentile([40, 10, 30, 20], 50), 25)
        self.assertEqual(percentile([10, 20, 30, 40], 95), 38.5)
        self.assertEqual(percentile([10, 20, 30, 40], 99), 39.7)

    def test_parse_memory_usage_converts_to_mib(self) -> None:
        usage, limit = parse_memory_usage("12.5MiB / 0.5GiB")
        self.assertEqual(usage, 12.5)
        self.assertEqual(limit, 512)

    def test_resource_summary_aggregates_per_service_per_rate(self) -> None:
        rows = [
            {
                "timestamp_utc": timestamp,
                "elapsed_seconds": str(index),
                "arrival_rate_rps": "5",
                "service": service,
                "cpu_percent": str(index * 10),
                "memory_usage_mib": str(index * 2),
                "memory_limit_mib": "512",
            }
            for index, timestamp in enumerate(("t1", "t2"), start=1)
            for service in ("api", "postgres", "redis")
        ]

        result = resource_summary(rows, 5)

        self.assertEqual(result["resource_samples"], 2)
        self.assertEqual(result["api_cpu_avg"], 15)
        self.assertEqual(result["api_cpu_max"], 20)
        self.assertEqual(result["api_memory_avg"], 3)
        self.assertEqual(result["api_memory_max"], 4)
        self.assertEqual(result["api_memory_limit_mib"], 512)

    def test_read_k6_metrics_summarizes_latency_errors_and_drops(self) -> None:
        records = [
            ("http_req_duration", 10),
            ("http_req_duration", 20),
            ("http_req_duration", 30),
            ("http_reqs", 1),
            ("http_reqs", 1),
            ("http_reqs", 1),
            ("http_req_failed", 0),
            ("http_req_failed", 1),
            ("http_req_failed", 0),
            ("checks", 1),
            ("checks", 0),
            ("dropped_iterations", 2),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "metrics.ndjson"
            path.write_text(
                "".join(
                    f'{{"type":"Point","metric":"{metric}",'
                    f'"data":{{"value":{value}}}}}\n'
                    for metric, value in records
                ),
                encoding="utf-8",
            )
            result = read_k6_metrics(path, duration_seconds=10)

        self.assertEqual(result["request_count"], 3)
        self.assertEqual(result["throughput_rps"], 0.3)
        self.assertEqual(result["http_failures"], 1)
        self.assertAlmostEqual(result["http_error_rate_pct"], 100 / 3)
        self.assertEqual(result["check_count"], 2)
        self.assertEqual(result["check_failures"], 1)
        self.assertEqual(result["dropped_iterations"], 2)
        self.assertEqual(result["p50_ms"], 20)
        self.assertEqual(result["p95_ms"], 29)
        self.assertEqual(result["p99_ms"], 29.8)
