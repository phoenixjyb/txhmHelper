"""Summarize stable exact/bucketed held-out artifact pairs without retraining."""
from __future__ import annotations

import argparse
from pathlib import Path

from hunl.gate_b_artifact_compare import compare_stable_artifacts, write_comparison
from hunl.gate_b_batch import build_held_out_jobs
from hunl.gate_b_validation import load_held_out_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("hunl/gate_b_heldout_cases_v1.json"))
    parser.add_argument("--seeds", required=True, help="Comma-separated independent integer seeds")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cuda-terminal-evaluator", action="store_true", help="Must match the artifacts being read")
    arguments = parser.parse_args()
    seeds = [int(value.strip()) for value in arguments.seeds.split(",") if value.strip()]
    jobs = build_held_out_jobs(load_held_out_cases(arguments.manifest), seeds, arguments.input_dir)
    report = compare_stable_artifacts(jobs, arguments.cuda_terminal_evaluator)
    write_comparison(arguments.output, report)
    print(report["stable_pair_count"], "stable pairs;", len(report["pending_jobs"]), "pending")


if __name__ == "__main__":
    main()
