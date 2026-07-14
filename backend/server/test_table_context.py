import unittest

from table_context import TableAction, normalize_table_context


class TableContextTest(unittest.TestCase):
    def test_maps_exact_bet_to_pot_relative_history(self):
        context = normalize_table_context(
            pot_before_street=10.0,
            effective_stack=100.0,
            hero_position="ip",
            actions=[TableAction("villain", "bet", 6.0)],
            bet_sizing=[0.33, 0.5, 1.0],
            raise_sizing=[0.75, 1.5],
        )

        self.assertEqual(["bet_60"], context.action_history)
        self.assertIn(0.6, context.bet_sizing)

    def test_maps_raise_using_increment_above_opponent_commitment(self):
        context = normalize_table_context(
            pot_before_street=10.0,
            effective_stack=100.0,
            hero_position="oop",
            actions=[
                TableAction("hero", "bet", 5.0),
                TableAction("villain", "raise", 18.0),
            ],
            bet_sizing=[0.33, 0.5, 1.0],
            raise_sizing=[0.75, 1.5],
        )

        self.assertEqual(["bet_50", "raise_130"], context.action_history)
        self.assertIn(1.3, context.raise_sizing)

    def test_rejects_line_when_hero_is_not_next_to_act(self):
        with self.assertRaisesRegex(ValueError, "opponent to act"):
            normalize_table_context(
                pot_before_street=10.0,
                effective_stack=100.0,
                hero_position="oop",
                actions=[TableAction("hero", "check")],
                bet_sizing=[0.5],
                raise_sizing=[1.0],
            )

    def test_rejects_complete_line(self):
        with self.assertRaisesRegex(ValueError, "street is complete"):
            normalize_table_context(
                pot_before_street=10.0,
                effective_stack=100.0,
                hero_position="oop",
                actions=[TableAction("hero", "bet", 5.0), TableAction("villain", "call")],
                bet_sizing=[0.5],
                raise_sizing=[1.0],
            )


if __name__ == "__main__":
    unittest.main()
