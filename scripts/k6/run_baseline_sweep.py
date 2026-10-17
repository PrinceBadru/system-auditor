import argparse
import csv
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("api", "postgres", "redis")
MEMORY_FACTORS = {
    "b": 1,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
}


def percentile(values: list[float], percentile_rank: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile from no values")
    index = (len(ordered) - 1) * percentile_rank / 100
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def parse_memory_value(value: str) -> float:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*", value)
    if match is None:
        raise ValueError(f"Unrecognized Docker memory value: {value!r}")
    amount, unit = match.groups()
    factor = MEMORY_FACTORS.get(unit.lower())
    if factor is None:
        raise ValueError(f"Unsupported Docker memory unit: {unit!r}")
    return float(amount) * factor / 1024**2


def parse_memory_usage(value: str) -> tuple[float, float]:
    usage, separator, limit = value.partition("/")
    if not separator:
        raise ValueError(f"Unrecognized Docker memory usage: {value!r}")
    return parse_memory_value(usage), parse_memory_value(limit)


def read_k6_metrics(path: Path, duration_seconds: int) -> dict[str, Any]:
    durations: list[float] = []
    requests = 0.0
    http_failures = 0.0
    check_count = 0
    check_failures = 0
    dropped_iterations = 0.0

    with path.open(encoding="utf-8") as metrics_file:
        for line in metrics_file:
            record = json.loads(line)
            if record.get("type") != "Point":
                continue
            metric = record.get("metric")
            value = float(record["data"]["value"])
            if metric == "http_req_duration":
                durations.append(value)
            elif metric == "http_reqs":
                requests += value
            elif metric == "http_req_failed":
                http_failures += value
            elif metric == "checks":
                check_count += 1
                check_failures += value == 0
            elif metric == "dropped_iterations":
                dropped_iterations += value

    result: dict[str, Any] = {
        "request_count": int(requests),
        "throughput_rps": requests / duration_seconds,
        "http_failures": int(http_failures),
        "http_error_rate_pct": http_failures / requests * 100 if requests else 0,
        "check_count": check_count,
        "check_failures": check_failures,
        "dropped_iterations": int(dropped_iterations),
    }
    for rank in (50, 95, 99):
        result[f"p{rank}_ms"] = percentile(durations, rank) if durations else ""
    return result


def run_command(
    arguments: list[str], *, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(arguments)}\n{detail}"
        )
    return result


def get_containers() -> dict[str, str]:
    containers: dict[str, str] = {}
    for service in SERVICES:
        result = run_command(
            ["docker", "compose", "ps", "--status", "running", "-q", service]
        )
        container_id = result.stdout.strip()
        if not container_id:
            raise RuntimeError(
                f"Compose service {service!r} is not running. Start the development "
                "stack and wait for its healthchecks before running the sweep."
            )
        containers[service] = container_id
    return containers


def sample_container_stats(
    containers: dict[str, str],
) -> dict[str, dict[str, float]]:
    result = run_command(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            *containers.values(),
        ],
        timeout=15,
    )
    records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    samples: dict[str, dict[str, float]] = {}
    for service, container_id in containers.items():
        record = next(
            (
                item
                for item in records
                if any(
                    str(item.get(field, ""))
                    .lower()
                    .startswith(container_id[:12].lower())
                    for field in ("ID", "Container")
                )
            ),
            None,
        )
        if record is None:
            raise RuntimeError(f"docker stats returned no sample for {service}")
        usage, limit = parse_memory_usage(record["MemUsage"])
        samples[service] = {
            "cpu_percent": float(record["CPUPerc"].rstrip("%")),
            "memory_usage_mib": usage,
            "memory_limit_mib": limit,
        }
    return samples


def sample_during_run(
    process: subprocess.Popen[bytes],
    rate: int,
    containers: dict[str, str],
    resources_writer: csv.DictWriter,
    resource_errors: list[str],
    interval: float,
) -> None:
    started = time.monotonic()
    next_sample = started
    while True:
        now = time.monotonic()
        if now >= next_sample:
            elapsed = now - started
            try:
                samples = sample_container_stats(containers)
                timestamp = datetime.now(UTC).isoformat()
                for service, sample in samples.items():
                    resources_writer.writerow(
                        {
                            "timestamp_utc": timestamp,
                            "elapsed_seconds": round(elapsed, 3),
                            "arrival_rate_rps": rate,
                            "service": service,
                            **sample,
                        }
                    )
            except (
                OSError,
                RuntimeError,
                ValueError,
                KeyError,
                subprocess.SubprocessError,
            ) as error:
                message = (
                    f"rate={rate} elapsed_seconds={elapsed:.3f}: "
                    f"resource sample failed: {error}"
                )
                resource_errors.append(message)
                print(message, file=sys.stderr)
            next_sample = max(next_sample + interval, time.monotonic() + interval)

        if process.poll() is not None:
            break
        time.sleep(min(0.1, max(0, next_sample - time.monotonic())))


def resource_summary(rows: list[dict[str, str]], rate: int) -> dict[str, Any]:
    matching_rows = [row for row in rows if int(row["arrival_rate_rps"]) == rate]
    sample_times = {
        (row["timestamp_utc"], row["elapsed_seconds"]) for row in matching_rows
    }
    summary: dict[str, Any] = {"resource_samples": len(sample_times)}
    for service in SERVICES:
        service_rows = [row for row in matching_rows if row["service"] == service]
        for metric, output_prefix in (
            ("cpu_percent", f"{service}_cpu"),
            ("memory_usage_mib", f"{service}_memory"),
        ):
            values = [float(row[metric]) for row in service_rows]
            summary[f"{output_prefix}_avg"] = (
                round(sum(values) / len(values), 2) if values else ""
            )
            summary[f"{output_prefix}_max"] = round(max(values), 2) if values else ""
        limits = [float(row["memory_limit_mib"]) for row in service_rows]
        summary[f"{service}_memory_limit_mib"] = round(limits[-1], 2) if limits else ""
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a sequential k6 open-model sweep and sample Compose resources."
    )
    parser.add_argument(
        "--rates",
        nargs="+",
        type=int,
        default=[5, 10, 15, 20, 25],
        help="ascending arrival rates in iterations per second (default: 5 10 15 20 25)",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=30,
        help="duration per rate (default: 30)",
    )
    parser.add_argument(
        "--sample-interval-seconds",
        type=float,
        default=1,
        help="Docker resource sampling interval (default: 1)",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=int,
        default=5,
        help="idle time between rates (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="new directory for results (default: timestamped directory in artifacts/k6)",
    )
    args = parser.parse_args()
    if not args.rates or any(rate < 1 for rate in args.rates):
        parser.error("rates must be positive integers")
    if args.rates != sorted(set(args.rates)):
        parser.error("rates must be unique and in ascending order")
    if args.duration_seconds < 1 or args.sample_interval_seconds <= 0:
        parser.error("duration and sample interval must be positive")
    if args.cooldown_seconds < 0:
        parser.error("cooldown cannot be negative")
    return args


def main() -> int:
    args = parse_args()
    for executable in ("docker", "k6"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"Required executable not found on PATH: {executable}")

    output_dir = args.output_dir
    if output_dir is None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_dir = ROOT / "artifacts" / "k6" / f"baseline-sweep-{stamp}"
    elif not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    containers = get_containers()
    sample_container_stats(containers)
    try:
        with urlopen("http://127.0.0.1:8000/health", timeout=3) as response:
            if response.status != 200:
                raise RuntimeError(f"API readiness returned HTTP {response.status}")
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"API readiness check failed: {error}") from error

    output_dir.mkdir(parents=True, exist_ok=False)
    k6_version = run_command(["k6", "version"]).stdout.strip()
    started_at = datetime.now(UTC)
    metadata = {
        "started_at_utc": started_at.isoformat(),
        "target": "http://127.0.0.1:8000/hello",
        "rates_rps": args.rates,
        "duration_seconds_per_rate": args.duration_seconds,
        "cooldown_seconds": args.cooldown_seconds,
        "resource_sample_interval_seconds": args.sample_interval_seconds,
        "k6_version": k6_version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    (output_dir / "run-info.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    resource_path = output_dir / "resource-samples.csv"
    resource_fields = (
        "timestamp_utc",
        "elapsed_seconds",
        "arrival_rate_rps",
        "service",
        "cpu_percent",
        "memory_usage_mib",
        "memory_limit_mib",
    )
    all_resource_rows: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    resource_errors: list[str] = []

    with resource_path.open("w", newline="", encoding="utf-8") as resource_file:
        resource_writer = csv.DictWriter(resource_file, fieldnames=resource_fields)
        resource_writer.writeheader()
        for index, rate in enumerate(args.rates):
            raw_path = output_dir / f"arrival-{rate}rps.ndjson"
            summary_path = output_dir / f"arrival-{rate}rps-k6-summary.json"
            stdout_path = output_dir / f"arrival-{rate}rps.stdout.log"
            stderr_path = output_dir / f"arrival-{rate}rps.stderr.log"
            print(f"Running {rate} iterations/second for {args.duration_seconds}s...")
            command = [
                "k6",
                "run",
                "--out",
                f"json={raw_path}",
                "--summary-export",
                str(summary_path),
                "-e",
                f"ARRIVAL_RATE={rate}",
                "-e",
                f"DURATION_SECONDS={args.duration_seconds}",
                str(ROOT / "scripts" / "k6" / "baseline-arrival.js"),
            ]
            with (
                stdout_path.open("w", encoding="utf-8") as stdout_file,
                stderr_path.open("w", encoding="utf-8") as stderr_file,
            ):
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdout=stdout_file,
                    stderr=stderr_file,
                )
                sample_during_run(
                    process,
                    rate,
                    containers,
                    resource_writer,
                    resource_errors,
                    args.sample_interval_seconds,
                )
                exit_code = process.wait()
            resource_file.flush()
            if not raw_path.exists():
                raise RuntimeError(f"k6 produced no raw metric output for {rate} rps")
            metrics = read_k6_metrics(raw_path, args.duration_seconds)
            results.append(
                {
                    "arrival_rate_rps": rate,
                    "duration_seconds": args.duration_seconds,
                    **metrics,
                    "k6_exit_code": exit_code,
                }
            )
            print(
                f"Completed {rate} iterations/second "
                f"(k6 exit code {exit_code}); raw metrics: {raw_path}"
            )
            if index < len(args.rates) - 1:
                time.sleep(args.cooldown_seconds)

    with resource_path.open(encoding="utf-8", newline="") as resource_file:
        all_resource_rows = list(csv.DictReader(resource_file))

    for result in results:
        result.update(resource_summary(all_resource_rows, result["arrival_rate_rps"]))
    fields = list(results[0])
    summary_csv = output_dir / "baseline-summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    (output_dir / "baseline-summary.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    if resource_errors:
        (output_dir / "resource-sampling-errors.log").write_text(
            "\n".join(resource_errors) + "\n", encoding="utf-8"
        )

    failed_results = [
        result
        for result in results
        if result["k6_exit_code"] != 0
        or result["request_count"] == 0
        or result["p50_ms"] == ""
        or result["http_failures"]
        or result["check_failures"]
        or result["dropped_iterations"]
        or result["resource_samples"] == 0
    ]
    print(f"Summary: {summary_csv}")
    if failed_results or resource_errors:
        print(
            "Sweep completed with recorded HTTP/check failures, dropped iterations, "
            "k6 errors, or resource-sampling gaps; inspect the summary and logs.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Baseline sweep could not run: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    raise SystemExit(exit_code)
