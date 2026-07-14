"""Held-out exact-versus-bucketed validation for the Gate B flop abstraction.

This compares two fresh CFR+ runs over identical sampled deals: one preserves
the exact private/public information sets and the other uses Gate B buckets.
It measures abstraction-induced root-policy drift; it does not estimate
exploitability or certify a full-game GTO solution.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, Sequence

from .buckets import board_texture_bucket, private_hand_bucket
from .game import GameConfig
from .turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


@dataclass(frozen=True)
class HeldOutFlopCase:
    case_id: str
    hero_hand: tuple[str, str]
    flop_board: tuple[str, str, str]
    pot_bb: float
    stack_bb: float
    hero_position: str = "oop"

    @property
    def board_bucket(self) -> str:
        return board_texture_bucket(self.flop_board)

    @property
    def private_bucket(self) -> str:
        return private_hand_bucket(self.hero_hand, self.flop_board)


def load_held_out_cases(path: str | Path) -> list[HeldOutFlopCase]:
    """Load a versioned fixed-spot manifest outside the training pilot set."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("manifest_version") != "gate_b_heldout_cases_v1":
        raise ValueError("Unsupported held-out Gate B manifest version.")
    cases = [_case_from_payload(item) for item in payload.get("cases", [])]
    if not cases:
        raise ValueError("Held-out Gate B manifest must contain at least one case.")
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Held-out Gate B case ids must be unique.")
    return cases


def compare_held_out_case(
    case: HeldOutFlopCase,
    iterations: int,
    seed: int,
    game: GameConfig | None = None,
    use_gpu_terminal_evaluator: bool = False,
) -> Dict[str, object]:
    """Compare exact and bucketed root policies using identical chance samples."""
    if iterations < 1:
        raise ValueError("iterations must be positive.")
    game_config = game or FlopTurnRiverTrainingConfig().game
    common = dict(game=game_config, use_gpu_terminal_evaluator=use_gpu_terminal_evaluator)
    exact = FlopTurnRiverCfrPlus(
        FlopTurnRiverTrainingConfig(
            **common,
            use_board_texture_buckets=False,
            use_private_hand_buckets=False,
        )
    )
    bucketed = FlopTurnRiverCfrPlus(
        FlopTurnRiverTrainingConfig(
            **common,
            use_board_texture_buckets=True,
            use_private_hand_buckets=True,
        )
    )
    arguments = dict(
        hero_hand=case.hero_hand,
        flop_board=case.flop_board,
        pot_bb=case.pot_bb,
        stacks_bb=(case.stack_bb, case.stack_bb),
        hero_position=case.hero_position,
        iterations=iterations,
    )
    exact_result = exact.train_flop(**arguments, rng=random.Random(seed))
    bucketed_result = bucketed.train_flop(**arguments, rng=random.Random(seed))
    exact_strategy = exact_result.strategy
    bucketed_strategy = bucketed_result.strategy
    if set(exact_strategy) != set(bucketed_strategy):
        raise ValueError("Exact and bucketed runs produced incompatible root actions.")
    action_errors = {
        action: abs(exact_strategy[action] - bucketed_strategy[action])
        for action in exact_strategy
    }
    return {
        "case_id": case.case_id,
        "seed": seed,
        "iterations": iterations,
        "board_bucket": case.board_bucket,
        "private_bucket": case.private_bucket,
        "exact_node_count": exact_result.node_count,
        "bucketed_node_count": bucketed_result.node_count,
        "exact_strategy": exact_strategy,
        "bucketed_strategy": bucketed_strategy,
        "action_absolute_errors": action_errors,
        "max_root_action_error": max(action_errors.values()),
        "root_total_variation": sum(action_errors.values()) / 2.0,
        "terminal_evaluator": exact_result.terminal_evaluator,
    }


def run_held_out_comparison(
    cases: Iterable[HeldOutFlopCase],
    iterations: int,
    seeds: Sequence[int],
    game: GameConfig | None = None,
    use_gpu_terminal_evaluator: bool = False,
) -> Dict[str, object]:
    """Run every held-out case/seed pair and summarize by abstraction stratum."""
    if not seeds:
        raise ValueError("At least one seed is required.")
    results = [
        compare_held_out_case(case, iterations, seed, game, use_gpu_terminal_evaluator)
        for case in cases
        for seed in seeds
    ]
    strata: Dict[str, list[Dict[str, object]]] = {}
    for result in results:
        key = f"{result['board_bucket']}||{result['private_bucket']}"
        strata.setdefault(key, []).append(result)
    return {
        "report_version": "gate_b_heldout_exact_vs_bucketed_v1",
        "iterations_per_run": iterations,
        "seeds": list(seeds),
        "case_count": len({result["case_id"] for result in results}),
        "run_count": len(results),
        "terminal_evaluator": "cuda_batched" if use_gpu_terminal_evaluator else "cpu_reference",
        "summary": _summary(results),
        "strata": {key: _summary(values) for key, values in sorted(strata.items())},
        "results": results,
    }


def write_report(report: Dict[str, object], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(destination)


def _case_from_payload(payload: Dict[str, object]) -> HeldOutFlopCase:
    hero = tuple(str(card) for card in payload["hero_hand"])
    board = tuple(str(card) for card in payload["flop_board"])
    if len(hero) != 2 or len(board) != 3:
        raise ValueError("Held-out Gate B cases require two hero cards and three flop cards.")
    if len(set(hero + board)) != 5:
        raise ValueError("Held-out Gate B cases cannot contain duplicate cards.")
    return HeldOutFlopCase(
        case_id=str(payload["case_id"]),
        hero_hand=hero,
        flop_board=board,
        pot_bb=float(payload.get("pot_bb", 10.0)),
        stack_bb=float(payload.get("stack_bb", 90.0)),
        hero_position=str(payload.get("hero_position", "oop")),
    )


def _summary(results: Sequence[Dict[str, object]]) -> Dict[str, float | int]:
    max_errors = [float(result["max_root_action_error"]) for result in results]
    variations = [float(result["root_total_variation"]) for result in results]
    return {
        "run_count": len(results),
        "mean_max_root_action_error": sum(max_errors) / len(max_errors),
        "median_max_root_action_error": median(max_errors),
        "max_root_action_error": max(max_errors),
        "mean_root_total_variation": sum(variations) / len(variations),
        "median_root_total_variation": median(variations),
        "max_root_total_variation": max(variations),
    }
