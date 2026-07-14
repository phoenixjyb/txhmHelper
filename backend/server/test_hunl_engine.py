import unittest

from hunl.abstraction import canonical_board, public_state_key
from hunl.game import ActionKind, GameConfig, Street, advance_street, apply_action, initial_postflop_state, legal_actions
from hunl.turn_river import TurnRiverRequest, solve_turn_river


class HunlPublicStateTest(unittest.TestCase):
    def setUp(self):
        self.config = GameConfig()

    def test_suit_isomorphic_boards_share_a_canonical_key(self):
        self.assertEqual(canonical_board(["As", "Kd", "7h"]), canonical_board(["Ah", "Kc", "7s"]))

    def test_five_card_board_with_four_suits_and_a_duplicate_is_canonicalized(self):
        self.assertEqual(
            canonical_board(["As", "Kd", "7h", "2c", "Jh"]),
            canonical_board(["Ah", "Kc", "7s", "2d", "Js"]),
        )

    def test_check_through_turn_advances_to_river(self):
        state = initial_postflop_state(
            street=Street.TURN,
            board=["As", "Kd", "7h", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            first_to_act=0,
        )
        state = apply_action(state, legal_actions(state, self.config)[0], self.config)
        state = apply_action(state, legal_actions(state, self.config)[0], self.config)

        self.assertTrue(state.street_complete)
        river = advance_street(state, "9s")
        self.assertEqual(Street.RIVER, river.street)
        self.assertEqual(5, len(river.board))
        self.assertEqual(0, river.to_act)
        self.assertIsNone(river.aggressor)
        self.assertEqual(0, river.raise_count)
        self.assertEqual((), river.history)
        self.assertIn("turn", public_state_key(state, self.config.abstraction_version))

    def test_street_advance_does_not_carry_prior_aggressor_or_history(self):
        state = initial_postflop_state(
            street=Street.TURN,
            board=["As", "Kd", "7h", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            first_to_act=0,
        )
        bet = next(action for action in legal_actions(state, self.config) if action.label == "bet_50")
        state = apply_action(state, bet, self.config)
        call = next(action for action in legal_actions(state, self.config) if action.kind == ActionKind.CALL)
        river = advance_street(apply_action(state, call, self.config), "9s")

        check = next(action for action in legal_actions(river, self.config) if action.kind == ActionKind.CHECK)
        river = apply_action(river, check, self.config)
        river = apply_action(river, next(action for action in legal_actions(river, self.config) if action.kind == ActionKind.CHECK), self.config)
        self.assertTrue(river.street_complete)

    def test_near_zero_stack_cannot_create_zero_chip_bet(self):
        state = initial_postflop_state(
            street=Street.RIVER,
            board=["As", "Kd", "7h", "2c", "9s"],
            pot_bb=10.0,
            stacks_bb=(1e-14, 1e-14),
            first_to_act=0,
        )
        self.assertEqual((ActionKind.CHECK,), tuple(action.kind for action in legal_actions(state, self.config)))

    def test_bet_raise_call_completes_street(self):
        state = initial_postflop_state(
            street=Street.TURN,
            board=["As", "Kd", "7h", "2c"],
            pot_bb=10.0,
            stacks_bb=(90.0, 90.0),
            first_to_act=0,
        )
        bet = next(action for action in legal_actions(state, self.config) if action.label == "bet_50")
        state = apply_action(state, bet, self.config)
        raise_action = next(action for action in legal_actions(state, self.config) if action.kind == ActionKind.RAISE)
        state = apply_action(state, raise_action, self.config)
        call = next(action for action in legal_actions(state, self.config) if action.kind == ActionKind.CALL)
        state = apply_action(state, call, self.config)

        self.assertTrue(state.street_complete)
        self.assertEqual(state.street_committed_bb[0], state.street_committed_bb[1])

    def test_turn_river_gate_returns_a_strategy(self):
        result = solve_turn_river(
            TurnRiverRequest(
                hero_hand=["As", "Kd"],
                turn_board=["Jh", "Td", "2c", "9s"],
                pot_bb=10.0,
                effective_stack_bb=100.0,
                hero_position="oop",
                action_history=[],
                iterations=100,
            )
        )

        self.assertAlmostEqual(1.0, sum(result.strategy.values()), places=8)
        self.assertIn("bet_75", result.strategy)

    def test_short_stack_all_in_call_returns_uncalled_chips(self):
        state = initial_postflop_state(
            street=Street.TURN,
            board=["As", "Kd", "7h", "2c"],
            pot_bb=10.0,
            stacks_bb=(5.0, 90.0),
            first_to_act=1,
        )
        bet = next(action for action in legal_actions(state, self.config) if action.label == "bet_100")
        state = apply_action(state, bet, self.config)
        all_in = next(action for action in legal_actions(state, self.config) if action.kind == ActionKind.ALL_IN)
        state = apply_action(state, all_in, self.config)

        self.assertTrue(state.street_complete)
        self.assertEqual(5.0, state.street_committed_bb[0])
        self.assertEqual(5.0, state.street_committed_bb[1])


if __name__ == "__main__":
    unittest.main()
