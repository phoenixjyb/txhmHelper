"""Run resumable, sequential paired stability jobs for a held-out Gate B manifest."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

from hunl.gate_b_batch import build_held_out_jobs, stable_report_summary, write_json_atomic
from hunl.gate_b_validation import load_held_out_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("hunl/gate_b_heldout_cases_v1.json"))
    parser.add_argument("--seeds", required=True, help="Comma-separated independent integer seeds")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--iterations-per-job", type=int, default=800)
    parser.add_argument("--checkpoint-interval", type=int, default=25)
    parser.add_argument("--job-timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-artifact-mb", type=int, default=2048)
    parser.add_argument("--max-jobs", type=int, default=0, help="0 runs every planned job")
    parser.add_argument(
        "--full-budget",
        action="store_true",
        help="Run every requested iteration even after within-seed stability; use for cross-seed convergence pilots.",
    )
    parser.add_argument("--cuda-terminal-evaluator", action="store_true")
    arguments = parser.parse_args()
    if min(arguments.iterations_per_job, arguments.checkpoint_interval, arguments.job_timeout_seconds, arguments.max_artifact_mb) < 1:
        raise ValueError("Iteration, interval, timeout, and artifact limits must be positive.")

    seeds = [int(value.strip()) for value in arguments.seeds.split(",") if value.strip()]
    jobs = build_held_out_jobs(load_held_out_cases(arguments.manifest), seeds, arguments.output_dir)
    if arguments.max_jobs:
        jobs = jobs[: arguments.max_jobs]
    records: list[Dict[str, object]] = []
    started = time.monotonic()
    for job in jobs:
        record = _run_job(job, arguments)
        records.append(record)
        _write_summary(arguments, records, started)
        print(json.dumps(record, sort_keys=True), flush=True)
    _write_summary(arguments, records, started)


def _run_job(job, arguments: argparse.Namespace) -> Dict[str, object]:
    stable = stable_report_summary(job.report)
    if stable is not None:
        return {"label": job.label, "status": "already_stable", **stable}

    artifacts = (job.exact_artifact, job.bucketed_artifact)
    present = [path.exists() for path in artifacts]
    if any(present) and not all(present):
        return {"label": job.label, "status": "incomplete_artifact_pair", "artifacts": [str(path) for path in artifacts]}

    command = [
        sys.executable,
        "train_gate_b_paired.py",
        "--hero",
        ",".join(job.case.hero_hand),
        "--board",
        ",".join(job.case.flop_board),
        "--pot-bb",
        str(job.case.pot_bb),
        "--stack-bb",
        str(job.case.stack_bb),
        "--iterations",
        str(arguments.iterations_per_job),
        "--checkpoint-interval",
        str(arguments.checkpoint_interval),
        "--exact-artifact",
        str(job.exact_artifact),
        "--bucketed-artifact",
        str(job.bucketed_artifact),
        "--report",
        str(job.report),
        "--seed",
        str(job.seed),
    ]
    if not arguments.full_budget:
        command.append("--stop-on-stable")
    if all(present):
        command.append("--resume")
    if arguments.cuda_terminal_evaluator:
        command.append("--cuda-terminal-evaluator")

    job.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with job.log.open("a", encoding="utf-8") as log:
            subprocess.run(
                command,
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=arguments.job_timeout_seconds,
            )
    except subprocess.TimeoutExpired:
        return {"label": job.label, "status": "timeout", "elapsed_seconds": time.monotonic() - started}
    except subprocess.CalledProcessError as error:
        return {"label": job.label, "status": "failed", "exit_code": error.returncode, "elapsed_seconds": time.monotonic() - started}

    max_bytes = arguments.max_artifact_mb * 1024 * 1024
    sizes = {path.name: path.stat().st_size for path in artifacts}
    if any(size > max_bytes for size in sizes.values()):
        return {"label": job.label, "status": "artifact_limit_exceeded", "artifact_sizes": sizes, "elapsed_seconds": time.monotonic() - started}
    stable = stable_report_summary(job.report)
    return {
        "label": job.label,
        "status": "stable" if stable is not None else "unstable_after_budget",
        "elapsed_seconds": time.monotonic() - started,
        "artifact_sizes": sizes,
        **(stable or {}),
    }


def _write_summary(arguments: argparse.Namespace, records: list[Dict[str, object]], started: float) -> None:
    statuses: Dict[str, int] = {}
    for record in records:
        statuses[str(record["status"])] = statuses.get(str(record["status"]), 0) + 1
    write_json_atomic(
        arguments.output_dir / "batch-summary.json",
        {
            "report_version": "gate_b_heldout_stability_batch_v1",
            "manifest": str(arguments.manifest),
            "seeds": arguments.seeds,
            "iterations_per_job": arguments.iterations_per_job,
            "checkpoint_interval": arguments.checkpoint_interval,
            "job_timeout_seconds": arguments.job_timeout_seconds,
            "max_artifact_mb": arguments.max_artifact_mb,
            "full_budget": arguments.full_budget,
            "cuda_terminal_evaluator": arguments.cuda_terminal_evaluator,
            "elapsed_seconds": time.monotonic() - started,
            "status_counts": statuses,
            "records": records,
        },
    )


if __name__ == "__main__":
    main()
