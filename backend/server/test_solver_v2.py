import random
import unittest

from solver_v2 import HeadsUpPostflopCfr, WeightedCombo


class HeadsUpPostflopCfrTest(unittest.TestCase):
    def setUp(self):
        self.solver = HeadsUpPostflopCfr(
            pot=10.0,
            effective_stack=100.0,
            bet_sizes=[0.33, 0.5, 1.0],
            raise_sizes=[0.75, 1.5],
            raise_cap=1,
        )

    def test_oop_root_strategy_is_normalized(self):
        result = self.solver.solve(
            hero_hand=["As", "Kd"],
            public_board=["Jh", "Td", "2c"],
            hero_position="oop",
            action_history=[],
            villain_range=None,
            iterations=150,
            rng=random.Random(7),
        )

        self.assertEqual(set(result.strategy), {"check", "bet_33", "bet_50", "bet_100"})
        self.assertAlmostEqual(sum(result.strategy.values()), 1.0, places=8)
        self.assertGreater(result.node_count, 1)

    def test_ip_hero_can_solve_after_villain_check(self):
        result = self.solver.solve(
            hero_hand=["As", "Kd"],
            public_board=["Jh", "Td", "2c"],
            hero_position="ip",
            action_history=["check"],
            villain_range=None,
            iterations=150,
            rng=random.Random(9),
        )

        self.assertIn("check", result.strategy)
        self.assertAlmostEqual(sum(result.strategy.values()), 1.0, places=8)

    def test_facing_bet_exposes_fold_call_and_raises(self):
        result = self.solver.solve(
            hero_hand=["As", "Kd"],
            public_board=["Jh", "Td", "2c"],
            hero_position="ip",
            action_history=["bet_50"],
            villain_range=[WeightedCombo(("Qs", "Qd"), 1.0)],
            iterations=150,
            rng=random.Random(3),
        )

        self.assertTrue({"fold", "call", "raise_75", "raise_150"}.issubset(result.strategy))
        self.assertAlmostEqual(sum(result.strategy.values()), 1.0, places=8)

    def test_rejects_when_hero_is_not_next_to_act(self):
        with self.assertRaisesRegex(ValueError, "Hero to be the next player"):
            self.solver.solve(
                hero_hand=["As", "Kd"],
                public_board=["Jh", "Td", "2c"],
                hero_position="ip",
                action_history=[],
                villain_range=None,
                iterations=100,
            )


if __name__ == "__main__":
    unittest.main()
