"""First offline solve gate: a turn root with sampled river showdowns.

This wrapper deliberately reuses the validated bounded CFR+ evaluator while the
four-street HUNL engine builds its own regret-store and chance traversal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

from solver_v2 import HeadsUpPostflopCfr, SolverResult, WeightedCombo


@dataclass(frozen=True)
class TurnRiverRequest:
    hero_hand: Sequence[str]
    turn_board: Sequence[str]
    pot_bb: float
    effective_stack_bb: float
    hero_position: str
    action_history: Sequence[str]
    villain_range: Sequence[WeightedCombo] | None = None
    iterations: int = 10_000


def solve_turn_river(request: TurnRiverRequest) -> SolverResult:
    if len(request.turn_board) != 4:
        raise ValueError("The turn/river gate requires exactly four board cards.")
    solver = HeadsUpPostflopCfr(
        pot=request.pot_bb,
        effective_stack=request.effective_stack_bb,
        bet_sizes=(0.33, 0.5, 0.75, 1.0, 1.5),
        raise_sizes=(0.75, 1.5),
        raise_cap=1,
        rake_pct=0.05,
        rake_cap=3.0,
    )
    return solver.solve(
        hero_hand=request.hero_hand,
        public_board=request.turn_board,
        hero_position=request.hero_position,
        action_history=request.action_history,
        villain_range=request.villain_range,
        iterations=request.iterations,
    )
