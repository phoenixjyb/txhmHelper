import random
import unittest

from hunl.gate_b_stability import run_paired_checkpoint, stable_after_recent_checkpoints
from hunl.game import GameConfig
from hunl.turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


class GateBStabilityTest(unittest.TestCase):
    def test_paired_checkpoint_uses_matching_samples_and_tracks_both_deltas(self):
        game = GameConfig(rake_pct=0.0, postflop_bet_sizes=(0.5,), postflop_raise_sizes=(1.0,), max_raises_per_street=1)
        exact = FlopTurnRiverCfrPlus(FlopTurnRiverTrainingConfig(game=game, use_board_texture_buckets=False, use_private_hand_buckets=False))
        bucketed = FlopTurnRiverCfrPlus(FlopTurnRiverTrainingConfig(game=game))
        exact_rng, bucketed_rng = random.Random(7), random.Random(7)
        checkpoint, exact_strategy, bucketed_strategy = run_paired_checkpoint(
            exact, bucketed,
            hero_hand=("As", "Kd"), flop_board=("Jh", "Td", "2c"), pot_bb=10.0, stack_bb=90.0,
            iterations=2, exact_rng=exact_rng, bucketed_rng=bucketed_rng,
        )
        self.assertIsNone(checkpoint.exact_root_delta)
        self.assertIsNone(checkpoint.bucketed_root_delta)
        self.assertEqual(exact_rng.getstate(), bucketed_rng.getstate())
        checkpoint, _, _ = run_paired_checkpoint(
            exact, bucketed,
            hero_hand=("As", "Kd"), flop_board=("Jh", "Td", "2c"), pot_bb=10.0, stack_bb=90.0,
            iterations=2, exact_rng=exact_rng, bucketed_rng=bucketed_rng,
            previous_exact_strategy=exact_strategy, previous_bucketed_strategy=bucketed_strategy,
        )
        self.assertIsNotNone(checkpoint.exact_root_delta)
        self.assertIsNotNone(checkpoint.bucketed_root_delta)

    def test_stability_requires_four_low_drift_checkpoints_for_both_models(self):
        history = [{"exact_root_delta": 0.009, "bucketed_root_delta": 0.009}] * 4
        self.assertTrue(stable_after_recent_checkpoints(history, 0.01))
        self.assertFalse(stable_after_recent_checkpoints(history[:3], 0.01))
        self.assertFalse(stable_after_recent_checkpoints(history[:-1] + [{"exact_root_delta": 0.02, "bucketed_root_delta": 0.009}], 0.01))


if __name__ == "__main__":
    unittest.main()
