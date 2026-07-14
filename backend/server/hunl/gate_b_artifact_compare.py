"""Compare already-stable exact and bucketed Gate B artifacts without retraining."""
from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Dict, Iterable

from .gate_b_batch import HeldOutBatchJob, stable_report_summary
from .turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


def compare_stable_artifacts(
    jobs: Iterable[HeldOutBatchJob], use_gpu_terminal_evaluator: bool
) -> Dict[str, object]:
    """Read stable artifact roots and group exact-versus-bucketed error by stratum."""
    results = []
    pending = []
    exact_config = FlopTurnRiverTrainingConfig(
        use_gpu_terminal_evaluator=use_gpu_terminal_evaluator,
        use_board_texture_buckets=False,
        use_private_hand_buckets=False,
    )
    bucketed_config = FlopTurnRiverTrainingConfig(
        use_gpu_terminal_evaluator=use_gpu_terminal_evaluator,
        use_board_texture_buckets=True,
        use_private_hand_buckets=True,
    )
    for job in jobs:
        stable = stable_report_summary(job.report)
        if stable is None:
            pending.append(job.label)
            continue
        exact = FlopTurnRiverCfrPlus.load_artifact(job.exact_artifact, exact_config)
        bucketed = FlopTurnRiverCfrPlus.load_artifact(job.bucketed_artifact, bucketed_config)
        exact_strategy = exact.flop_root_strategy(
            job.case.hero_hand, job.case.flop_board, job.case.pot_bb, (job.case.stack_bb, job.case.stack_bb)
        )
        bucketed_strategy = bucketed.flop_root_strategy(
            job.case.hero_hand, job.case.flop_board, job.case.pot_bb, (job.case.stack_bb, job.case.stack_bb)
        )
        if set(exact_strategy) != set(bucketed_strategy):
            raise ValueError(f"Stable artifact pair {job.label} has incompatible root actions.")
        action_errors = {action: abs(exact_strategy[action] - bucketed_strategy[action]) for action in exact_strategy}
        results.append(
            {
                "label": job.label,
                "case_id": job.case.case_id,
                "seed": job.seed,
                "board_bucket": job.case.board_bucket,
                "private_bucket": job.case.private_bucket,
                "total_iterations": stable["total_iterations"],
                "exact_strategy": exact_strategy,
                "bucketed_strategy": bucketed_strategy,
                "action_absolute_errors": action_errors,
                "max_root_action_error": max(action_errors.values()),
                "root_total_variation": sum(action_errors.values()) / 2.0,
            }
        )
    strata: Dict[str, list[Dict[str, object]]] = {}
    for result in results:
        key = f"{result['board_bucket']}||{result['private_bucket']}"
        strata.setdefault(key, []).append(result)
    return {
        "report_version": "gate_b_stable_artifact_comparison_v1",
        "stable_pair_count": len(results),
        "pending_jobs": pending,
        "summary": _summary(results) if results else None,
        "strata": {key: _summary(values) for key, values in sorted(strata.items())},
        "results": results,
    }


def write_comparison(path: str | Path, report: Dict[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    import json

    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(destination)


def _summary(results: list[Dict[str, object]]) -> Dict[str, float | int]:
    errors = [float(result["max_root_action_error"]) for result in results]
    variations = [float(result["root_total_variation"]) for result in results]
    return {
        "pair_count": len(results),
        "mean_max_root_action_error": sum(errors) / len(errors),
        "median_max_root_action_error": median(errors),
        "max_root_action_error": max(errors),
        "mean_root_total_variation": sum(variations) / len(variations),
        "median_root_total_variation": median(variations),
        "max_root_total_variation": max(variations),
    }
