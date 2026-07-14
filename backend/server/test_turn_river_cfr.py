import random
import tempfile
import unittest
from pathlib import Path

from hunl.game import GameConfig
from hunl.turn_river_cfr import (
    FLOP_TURN_RIVER_ARTIFACT_VERSION,
    FlopTurnRiverCfrPlus,
    FlopTurnRiverTrainingConfig,
    TurnRiverCfrPlus,
    TurnRiverTrainingConfig,
)

try:
    import torch
except ImportError:
    torch = None


def gate_config(use_gpu_terminal_evaluator: bool = False) -> TurnRiverTrainingConfig:
    return TurnRiverTrainingConfig(
        game=GameConfig(
            rake_pct=0.0,
            postflop_bet_sizes=(0.5,),
            postflop_raise_sizes=(1.0,),
            max_raises_per_street=1,
        ),
        use_gpu_terminal_evaluator=use_gpu_terminal_evaluator,
    )


class TurnRiverCfrPlusTest(unittest.TestCase):
    def train_arguments(self):
        return dict(
            hero_hand=["As", "Kd"],
            turn_board=["Jh", "Td", "2c", "7h"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            hero_position="oop",
        )

    def test_traverses_real_river_nodes_and_returns_root_strategy(self):
        trainer = TurnRiverCfrPlus(gate_config())
        result = trainer.train(**self.train_arguments(), iterations=12, rng=random.Random(7))

        self.assertAlmostEqual(1.0, sum(result.strategy.values()), places=8)
        self.assertIn("check", result.strategy)
        self.assertIn("bet_50", result.strategy)
        self.assertGreater(result.node_count, 12)
        self.assertTrue(any("|river|" in key for key in trainer.nodes))

    def test_artifact_can_resume_cumulative_regrets(self):
        trainer = TurnRiverCfrPlus(gate_config())
        trainer.train(**self.train_arguments(), iterations=8, rng=random.Random(11))
        before = len(trainer.nodes)

        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "turn-river.json"
            trainer.save_artifact(artifact, metadata={"spot": "unit-test"})
            resumed = TurnRiverCfrPlus.load_artifact(artifact, gate_config())
            self.assertEqual(
                trainer.root_strategy(**self.train_arguments()),
                resumed.root_strategy(**self.train_arguments()),
            )
            result = resumed.train(**self.train_arguments(), iterations=8, rng=random.Random(12))

        self.assertGreaterEqual(result.node_count, before)
        self.assertEqual(16, result.total_iterations)
        self.assertAlmostEqual(1.0, sum(result.strategy.values()), places=8)

    def test_flop_gate_traverses_flop_turn_and_river_information_sets(self):
        config = FlopTurnRiverTrainingConfig(
            game=GameConfig(
                rake_pct=0.0,
                postflop_bet_sizes=(0.5,),
                postflop_raise_sizes=(1.0,),
                max_raises_per_street=1,
            )
        )
        trainer = FlopTurnRiverCfrPlus(config)
        result = trainer.train_flop(
            hero_hand=["As", "Kd"],
            flop_board=["Jh", "Td", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            hero_position="oop",
            iterations=3,
            rng=random.Random(77),
        )

        self.assertEqual(FLOP_TURN_RIVER_ARTIFACT_VERSION, result.artifact_version)
        self.assertAlmostEqual(1.0, sum(result.strategy.values()), places=8)
        self.assertTrue(any("|flop|" in key for key in trainer.nodes))
        self.assertTrue(any("|turn|" in key for key in trainer.nodes))
        self.assertTrue(any("|river|" in key for key in trainer.nodes))
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "flop.json"
            trainer.save_artifact(artifact)
            restored = FlopTurnRiverCfrPlus.load_artifact(artifact, config)
        self.assertEqual(len(trainer.nodes), len(restored.nodes))
        restored_strategy = restored.flop_root_strategy(
            hero_hand=["As", "Kd"],
            flop_board=["Jh", "Td", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
        )
        for action, probability in result.strategy.items():
            self.assertAlmostEqual(probability, restored_strategy[action], places=12)

    @unittest.skipUnless(torch is not None and torch.cuda.is_available(), "CUDA PyTorch is not installed")
    def test_gpu_terminal_samples_match_cpu_strategy(self):
        cpu = TurnRiverCfrPlus(gate_config())
        gpu = TurnRiverCfrPlus(gate_config(use_gpu_terminal_evaluator=True))
        cpu_result = cpu.train(**self.train_arguments(), iterations=12, rng=random.Random(99))
        gpu_result = gpu.train(**self.train_arguments(), iterations=12, rng=random.Random(99))

        self.assertEqual("cpu_reference", cpu_result.terminal_evaluator)
        self.assertEqual("cuda_batched", gpu_result.terminal_evaluator)
        for action, value in cpu_result.strategy.items():
            self.assertAlmostEqual(value, gpu_result.strategy[action], places=10)


if __name__ == "__main__":
    unittest.main()
