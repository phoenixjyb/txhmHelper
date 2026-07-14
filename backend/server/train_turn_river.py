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
    parser.add_argument("--seed", type=int, default=20260714)
    arguments = parser.parse_args()

    config = TurnRiverTrainingConfig(use_gpu_terminal_evaluator=arguments.cuda_terminal_evaluator)
    if arguments.resume:
        trainer = TurnRiverCfrPlus.load_artifact(arguments.artifact, config)
    else:
        trainer = TurnRiverCfrPlus(config)
    result = trainer.train(
        hero_hand=_cards(arguments.hero, 2),
        turn_board=_cards(arguments.board, 4),
        pot_bb=arguments.pot_bb,
        stacks_bb=(arguments.stack_bb, arguments.stack_bb),
        hero_position="oop",
        iterations=arguments.iterations,
        rng=random.Random(arguments.seed),
    )
    trainer.save_artifact(
        arguments.artifact,
        metadata={
            "hero": _cards(arguments.hero, 2),
            "turn_board": _cards(arguments.board, 4),
            "pot_bb": arguments.pot_bb,
            "stack_bb": arguments.stack_bb,
            "seed": arguments.seed,
            "last_iterations": arguments.iterations,
        },
    )
    print(json.dumps({**result.__dict__, "artifact": str(arguments.artifact)}, sort_keys=True))


def _cards(value: str, expected: int) -> list[str]:
    cards = [card.strip() for card in value.split(",") if card.strip()]
    if len(cards) != expected:
        raise ValueError(f"Expected {expected} comma-separated cards.")
    return cards


if __name__ == "__main__":
    main()
