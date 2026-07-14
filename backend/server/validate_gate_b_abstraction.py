"""Run held-out exact-versus-bucketed validation for the Gate B flop model."""
from __future__ import annotations

import argparse
from pathlib import Path

from hunl.gate_b_validation import load_held_out_cases, run_held_out_comparison, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("hunl/gate_b_heldout_cases_v1.json"),
        help="Versioned held-out flop case manifest.",
    )
    parser.add_argument("--iterations", type=int, required=True, help="Fresh CFR+ iterations per exact/bucketed run.")
    parser.add_argument("--seeds", required=True, help="Comma-separated independent integer seeds.")
    parser.add_argument("--output", type=Path, required=True, help="JSON report path.")
    parser.add_argument("--cuda-terminal-evaluator", action="store_true")
    arguments = parser.parse_args()

    seeds = [int(value.strip()) for value in arguments.seeds.split(",") if value.strip()]
    report = run_held_out_comparison(
        load_held_out_cases(arguments.manifest),
        iterations=arguments.iterations,
        seeds=seeds,
        use_gpu_terminal_evaluator=arguments.cuda_terminal_evaluator,
    )
    write_report(report, arguments.output)
    print(arguments.output)
    print(report["summary"])


if __name__ == "__main__":
    main()
