"""Offline checkpointable training entry point for the HUNL turn/river Gate A."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from hunl.turn_river_cfr import TurnRiverCfrPlus, TurnRiverTrainingConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hero", required=True, help="Two cards, comma-separated; for example As,Kd")
    parser.add_argument("--board", required=True, help="Four turn cards, comma-separated")
    parser.add_argument("--pot-bb", type=float, required=True)
    parser.add_argument("--stack-bb", type=float, default=100.0, help="Effective remaining stack for both players")
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cuda-terminal-evaluator", action="store_true")
    parser.add_argument("--checkpoint-interval", type=int, default=0, help="Save/report after this many iterations")
    parser.add_argument("--max-root-policy-delta", type=float, default=None, help="Stop after a checkpoint reaches this delta")
    parser.add_argument("--seed", type=int, default=20260714)
    arguments = parser.parse_args()

    config = TurnRiverTrainingConfig(use_gpu_terminal_evaluator=arguments.cuda_terminal_evaluator)
    if arguments.resume:
        trainer = TurnRiverCfrPlus.load_artifact(arguments.artifact, config)
    else:
        trainer = TurnRiverCfrPlus(config)
    hero, board = _cards(arguments.hero, 2), _cards(arguments.board, 4)
    generator = random.Random(arguments.seed)
    interval = arguments.checkpoint_interval or arguments.iterations
    if interval < 1:
        raise ValueError("checkpoint_interval must be positive.")
    previous_strategy = (
        trainer.root_strategy(hero, board, arguments.pot_bb, (arguments.stack_bb, arguments.stack_bb))
        if arguments.resume
        else None
    )
    remaining = arguments.iterations
    while remaining > 0:
        step = min(interval, remaining)
        result = trainer.train(
            hero_hand=hero,
            turn_board=board,
            pot_bb=arguments.pot_bb,
            stacks_bb=(arguments.stack_bb, arguments.stack_bb),
            hero_position="oop",
            iterations=step,
            rng=generator,
        )
        delta = _max_policy_delta(previous_strategy, result.strategy) if previous_strategy else None
        trainer.save_artifact(
            arguments.artifact,
            metadata={
                "hero": hero,
                "turn_board": board,
                "pot_bb": arguments.pot_bb,
                "stack_bb": arguments.stack_bb,
                "seed": arguments.seed,
                "last_iterations": step,
                "total_iterations": result.total_iterations,
                "root_policy_delta_from_previous_checkpoint": delta,
            },
        )
        print(json.dumps({**result.__dict__, "artifact": str(arguments.artifact), "root_policy_delta": delta}, sort_keys=True))
        if delta is not None and arguments.max_root_policy_delta is not None and delta <= arguments.max_root_policy_delta:
            break
        previous_strategy = result.strategy
        remaining -= step


def _cards(value: str, expected: int) -> list[str]:
    cards = [card.strip() for card in value.split(",") if card.strip()]
    if len(cards) != expected:
        raise ValueError(f"Expected {expected} comma-separated cards.")
    return cards


def _max_policy_delta(previous: dict[str, float], current: dict[str, float]) -> float:
    if set(previous) != set(current):
        raise ValueError("Cannot compare root strategies with different action sets.")
    return max(abs(previous[action] - current[action]) for action in previous)


if __name__ == "__main__":
    main()
