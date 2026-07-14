import random
import unittest

from hunl.buckets import board_texture_bucket, private_hand_bucket
from hunl.game import GameConfig
from hunl.turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


class HunlBucketTest(unittest.TestCase):
    def test_board_texture_is_suit_isomorphic(self):
        self.assertEqual(
            board_texture_bucket(["As", "Kd", "7h", "2c"]),
            board_texture_bucket(["Ah", "Kc", "7s", "2d"]),
        )

    def test_private_bucket_preserves_relative_hand_and_draw_shape(self):
        self.assertEqual(
            private_hand_bucket(["As", "Kd"], ["Qs", "7d", "2c"]),
            private_hand_bucket(["Ah", "Kc"], ["Qh", "7c", "2s"]),
        )

    def test_private_bucket_preserves_hole_rank_pattern(self):
        board = ["Jc", "7d", "3s"]
        self.assertNotEqual(
            private_hand_bucket(["As", "Kd"], board),
            private_hand_bucket(["Qh", "9c"], board),
        )

    def test_bucketed_flop_abstraction_reduces_observed_information_sets(self):
        game = GameConfig(
            rake_pct=0.0,
            postflop_bet_sizes=(0.5,),
            postflop_raise_sizes=(1.0,),
            max_raises_per_street=1,
        )
        arguments = dict(
            hero_hand=["As", "Kd"],
            flop_board=["Jh", "Td", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            hero_position="oop",
            iterations=8,
        )
        exact = FlopTurnRiverCfrPlus(
            FlopTurnRiverTrainingConfig(game=game, use_board_texture_buckets=False, use_private_hand_buckets=False)
        )
        bucketed = FlopTurnRiverCfrPlus(FlopTurnRiverTrainingConfig(game=game))

        exact_result = exact.train_flop(**arguments, rng=random.Random(101))
        bucketed_result = bucketed.train_flop(**arguments, rng=random.Random(101))

        self.assertLess(bucketed_result.node_count, exact_result.node_count)
        self.assertAlmostEqual(1.0, sum(bucketed_result.strategy.values()), places=8)


if __name__ == "__main__":
    unittest.main()
