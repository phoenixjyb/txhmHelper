"""Compare stable Gate B artifacts across independent training seeds."""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable

from .gate_b_batch import HeldOutBatchJob, stable_report_summary
from .turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


def compare_cross_seed_stable_artifacts(
    jobs: Iterable[HeldOutBatchJob], use_gpu_terminal_evaluator: bool
) -> Dict[str, object]:
    """Measure root-policy drift among exact and bucketed artifacts per held-out case.

    This is deliberately separate from the exact-versus-bucketed comparison:
    it establishes whether independent training runs are repeatable before a
    cross-model policy difference is treated as abstraction error.
    """
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
    grouped: Dict[tuple[str, str], list[Dict[str, object]]] = {}
    pending = []
    for job in jobs:
        if stable_report_summary(job.report) is None:
            pending.append(job.label)
            continue
        common = dict(
            hero_hand=job.case.hero_hand,
            flop_board=job.case.flop_board,
            pot_bb=job.case.pot_bb,
            stacks_bb=(job.case.stack_bb, job.case.stack_bb),
        )
        for model, artifact, config in (
            ("exact", job.exact_artifact, exact_config),
            ("bucketed", job.bucketed_artifact, bucketed_config),
        ):
            trainer = FlopTurnRiverCfrPlus.load_artifact(artifact, config)
            grouped.setdefault((job.case.case_id, model), []).append(
                {
                    "label": job.label,
                    "seed": job.seed,
                    "strategy": trainer.flop_root_strategy(**common),
                }
            )

    reports = []
    for (case_id, model), artifacts in sorted(grouped.items()):
        pairs = []
        for left, right in combinations(artifacts, 2):
            distances = _policy_distances(left["strategy"], right["strategy"])
            pairs.append(
                {
                    "left_label": left["label"],
                    "right_label": right["label"],
                    **distances,
                }
            )
        reports.append(
            {
                "case_id": case_id,
                "model": model,
                "artifact_count": len(artifacts),
                "pair_count": len(pairs),
                "summary": _summary(pairs) if pairs else None,
                "pairs": pairs,
            }
        )
    return {
        "report_version": "gate_b_cross_seed_artifact_comparison_v1",
        "pending_jobs": pending,
        "required_artifacts_per_case": 3,
        "required_pairwise_max_root_action_error": 0.025,
        "groups": reports,
    }


def _policy_distances(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, object]:
    if set(left) != set(right):
        raise ValueError("Cross-seed artifacts have incompatible root actions.")
    action_errors = {action: abs(left[action] - right[action]) for action in left}
    return {
        "action_absolute_errors": action_errors,
        "max_root_action_error": max(action_errors.values()),
        "root_total_variation": sum(action_errors.values()) / 2.0,
    }


def _summary(pairs: list[Dict[str, object]]) -> Dict[str, float | int]:
    maxima = [float(pair["max_root_action_error"]) for pair in pairs]
    variations = [float(pair["root_total_variation"]) for pair in pairs]
    return {
        "pair_count": len(pairs),
        "max_root_action_error": max(maxima),
        "mean_max_root_action_error": sum(maxima) / len(maxima),
        "max_root_total_variation": max(variations),
        "mean_root_total_variation": sum(variations) / len(variations),
    }


def write_comparison(path: str | Path, report: Dict[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    import json

    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(destination)
