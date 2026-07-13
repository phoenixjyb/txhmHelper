import random
import unittest

from solver_cfr import StreetCFR, parse_cards, solve_cfr


class StreetCfrTest(unittest.TestCase):
    def test_preflop_strategy_is_normalized(self):
        strategy = solve_cfr(
            stage="preflop",
            hole=["As", "Kd"],
            board=[],
            pot=10.0,
            effective_stack=100.0,
            bet_sizes=[0.5, 1.0],
            iterations=100,
        )

        self.assertEqual(set(strategy), {"check", "bet_50", "bet_100"})
        self.assertAlmostEqual(sum(strategy.values()), 1.0, places=8)

    def test_information_sets_only_include_public_board(self):
        solver = StreetCFR(pot=10.0, effective_stack=100.0, bet_sizes=[0.5])
        hero = parse_cards(["As", "Kd"])
        flop = parse_cards(["Jh", "Td", "2c"])

        root = solver._info_key(0, hero, flop, ())
        later_runout = solver._info_key(0, hero, flop, ())

        self.assertEqual(root, later_runout)
        self.assertIn("Jh,Td,2c", root)

    def test_flop_strategy_has_a_root_node(self):
        solver = StreetCFR(pot=10.0, effective_stack=100.0, bet_sizes=[0.5])
        strategy = solver.solve(
            hero_hand=["As", "Kd"],
            public_board=["Jh", "Td", "2c"],
            iterations=80,
            rng=random.Random(7),
        )

        self.assertEqual(set(strategy), {"check", "bet_50"})
        self.assertAlmostEqual(sum(strategy.values()), 1.0, places=8)

    def test_stage_requires_the_matching_board_size(self):
        with self.assertRaisesRegex(ValueError, "flop requires 3 board cards"):
            solve_cfr(
                stage="flop",
                hole=["As", "Kd"],
                board=[],
                pot=10.0,
                effective_stack=100.0,
                iterations=1,
            )


if __name__ == "__main__":
    unittest.main()
