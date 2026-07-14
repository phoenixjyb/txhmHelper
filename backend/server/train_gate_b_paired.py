"""Checkpoint matched exact and bucketed Gate B trainers for one fixed flop spot."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from hunl.gate_b_stability import run_paired_checkpoint, stable_after_recent_checkpoints
from hunl.turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig
from train_turn_river import _as_tuple, _cards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hero", required=True, help="Two comma-separated cards; for example As,Kd")
    parser.add_argument("--board", required=True, help="Three comma-separated flop cards")
    parser.add_argument("--pot-bb", type=float, required=True)
    parser.add_argument("--stack-bb", type=float, default=100.0)
    parser.add_argument("--iterations", type=int, required=True, help="New paired iterations to run")
    parser.add_argument("--checkpoint-interval", type=int, required=True)
    parser.add_argument("--exact-artifact", type=Path, required=True)
    parser.add_argument("--bucketed-artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cuda-terminal-evaluator", action="store_true")
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--stability-threshold", type=float, default=0.01)
    parser.add_argument("--stop-on-stable", action="store_true")
    arguments = parser.parse_args()
    if arguments.iterations < 1 or arguments.checkpoint_interval < 1:
        raise ValueError("iterations and checkpoint_interval must be positive.")

    exact_config = FlopTurnRiverTrainingConfig(
        use_gpu_terminal_evaluator=arguments.cuda_terminal_evaluator,
        use_board_texture_buckets=False,
        use_private_hand_buckets=False,
    )
    bucketed_config = FlopTurnRiverTrainingConfig(
        use_gpu_terminal_evaluator=arguments.cuda_terminal_evaluator,
        use_board_texture_buckets=True,
        use_private_hand_buckets=True,
    )
    if arguments.resume:
        exact = FlopTurnRiverCfrPlus.load_artifact(arguments.exact_artifact, exact_config)
        bucketed = FlopTurnRiverCfrPlus.load_artifact(arguments.bucketed_artifact, bucketed_config)
        history = list(exact.artifact_metadata.get("paired_checkpoint_history", []))
        exact_rng = _rng_from_metadata(exact.artifact_metadata)
        bucketed_rng = _rng_from_metadata(bucketed.artifact_metadata)
        if exact_rng.getstate() != bucketed_rng.getstate():
            raise ValueError("Paired artifacts do not share the same chance-sampling RNG state.")
    else:
        exact = FlopTurnRiverCfrPlus(exact_config)
        bucketed = FlopTurnRiverCfrPlus(bucketed_config)
        history = []
        exact_rng = random.Random(arguments.seed)
        bucketed_rng = random.Random(arguments.seed)

    hero, board = _cards(arguments.hero, 2), _cards(arguments.board, 3)
    previous_exact = exact.flop_root_strategy(hero, board, arguments.pot_bb, (arguments.stack_bb, arguments.stack_bb)) if arguments.resume else None
    previous_bucketed = bucketed.flop_root_strategy(hero, board, arguments.pot_bb, (arguments.stack_bb, arguments.stack_bb)) if arguments.resume else None
    remaining = arguments.iterations
    while remaining:
        step = min(remaining, arguments.checkpoint_interval)
        checkpoint, previous_exact, previous_bucketed = run_paired_checkpoint(
            exact,
            bucketed,
            hero_hand=hero,
            flop_board=board,
            pot_bb=arguments.pot_bb,
            stack_bb=arguments.stack_bb,
            iterations=step,
            exact_rng=exact_rng,
            bucketed_rng=bucketed_rng,
            previous_exact_strategy=previous_exact,
            previous_bucketed_strategy=previous_bucketed,
        )
        history.append(checkpoint.to_dict())
        metadata = {
            "paired_run_version": "gate_b_paired_checkpoint_v1",
            "hero": hero,
            "flop_board": board,
            "pot_bb": arguments.pot_bb,
            "stack_bb": arguments.stack_bb,
            "seed": arguments.seed,
            "checkpoint_interval": arguments.checkpoint_interval,
            "paired_checkpoint_history": history,
        }
        exact.save_artifact(arguments.exact_artifact, metadata={**metadata, "rng_state": exact_rng.getstate()})
        bucketed.save_artifact(arguments.bucketed_artifact, metadata={**metadata, "rng_state": bucketed_rng.getstate()})
        report = {
            "report_version": "gate_b_paired_checkpoint_v1",
            "stable": stable_after_recent_checkpoints(history, arguments.stability_threshold),
            "stability_threshold": arguments.stability_threshold,
            "history": history,
        }
        _write_json(arguments.report, report)
        print(json.dumps(report, sort_keys=True))
        if report["stable"] and arguments.stop_on_stable:
            break
        remaining -= step


def _rng_from_metadata(metadata: dict[str, object]) -> random.Random:
    serialized_state = metadata.get("rng_state")
    if serialized_state is None:
        raise ValueError("Paired artifact cannot resume safely because it has no saved RNG state.")
    generator = random.Random()
    generator.setstate(_as_tuple(serialized_state))
    return generator


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    main()
