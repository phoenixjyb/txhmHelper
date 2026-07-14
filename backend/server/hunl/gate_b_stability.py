"""Paired exact/bucketed checkpoint training for one fixed Gate B flop spot."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Sequence

from .turn_river_cfr import FlopTurnRiverCfrPlus


@dataclass(frozen=True)
class PairedCheckpoint:
    checkpoint_iterations: int
    total_iterations: int
    exact_root_delta: float | None
    bucketed_root_delta: float | None
    cross_model_max_root_delta: float
    exact_node_count: int
    bucketed_node_count: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "checkpoint_iterations": self.checkpoint_iterations,
            "total_iterations": self.total_iterations,
            "exact_root_delta": self.exact_root_delta,
            "bucketed_root_delta": self.bucketed_root_delta,
            "cross_model_max_root_delta": self.cross_model_max_root_delta,
            "exact_node_count": self.exact_node_count,
            "bucketed_node_count": self.bucketed_node_count,
        }


def run_paired_checkpoint(
    exact: FlopTurnRiverCfrPlus,
    bucketed: FlopTurnRiverCfrPlus,
    *,
    hero_hand: Sequence[str],
    flop_board: Sequence[str],
    pot_bb: float,
    stack_bb: float,
    iterations: int,
    exact_rng: random.Random,
    bucketed_rng: random.Random,
    previous_exact_strategy: Dict[str, float] | None = None,
    previous_bucketed_strategy: Dict[str, float] | None = None,
) -> tuple[PairedCheckpoint, Dict[str, float], Dict[str, float]]:
    """Advance both models over matching chance samples and compare their roots."""
    arguments = dict(
        hero_hand=hero_hand,
        flop_board=flop_board,
        pot_bb=pot_bb,
        stacks_bb=(stack_bb, stack_bb),
        hero_position="oop",
        iterations=iterations,
    )
    exact_result = exact.train_flop(**arguments, rng=exact_rng)
    bucketed_result = bucketed.train_flop(**arguments, rng=bucketed_rng)
    exact_strategy = exact_result.strategy
    bucketed_strategy = bucketed_result.strategy
    checkpoint = PairedCheckpoint(
        checkpoint_iterations=iterations,
        total_iterations=exact_result.total_iterations,
        exact_root_delta=_max_policy_delta(previous_exact_strategy, exact_strategy),
        bucketed_root_delta=_max_policy_delta(previous_bucketed_strategy, bucketed_strategy),
        cross_model_max_root_delta=_max_policy_delta(exact_strategy, bucketed_strategy) or 0.0,
        exact_node_count=exact_result.node_count,
        bucketed_node_count=bucketed_result.node_count,
    )
    return checkpoint, exact_strategy, bucketed_strategy


def stable_after_recent_checkpoints(
    history: Sequence[Dict[str, object]], threshold: float, required: int = 4
) -> bool:
    """Return true only when both models have enough consecutive low-drift checkpoints."""
    if threshold <= 0 or required < 1 or len(history) < required:
        return False
    recent = history[-required:]
    return all(
        item.get("exact_root_delta") is not None
        and item.get("bucketed_root_delta") is not None
        and float(item["exact_root_delta"]) <= threshold
        and float(item["bucketed_root_delta"]) <= threshold
        for item in recent
    )


def _max_policy_delta(previous: Dict[str, float] | None, current: Dict[str, float]) -> float | None:
    if previous is None:
        return None
    if set(previous) != set(current):
        raise ValueError("Cannot compare strategies with different action sets.")
    return max(abs(previous[action] - current[action]) for action in previous)
