"""Four-street public game-state and action abstraction for HUNL 100bb v1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"

    def next(self) -> "Street":
        order = (Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER)
        index = order.index(self)
        if index == len(order) - 1:
            raise ValueError("River has no next street.")
        return order[index + 1]


class ActionKind(str, Enum):
    CHECK = "check"
    BET = "bet"
    CALL = "call"
    FOLD = "fold"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    target_commitment: float = 0.0
    size_label: str = ""

    @property
    def label(self) -> str:
        if self.kind in (ActionKind.BET, ActionKind.RAISE):
            return f"{self.kind.value}_{self.size_label}"
        return self.kind.value


@dataclass(frozen=True)
class GameConfig:
    abstraction_version: str = "hunl_100bb_v1"
    starting_stack_bb: float = 100.0
    small_blind_bb: float = 0.5
    big_blind_bb: float = 1.0
    rake_pct: float = 0.05
    rake_cap_bb: float = 3.0
    postflop_bet_sizes: Tuple[float, ...] = (0.33, 0.50, 0.75, 1.0, 1.5)
    postflop_raise_sizes: Tuple[float, ...] = (0.75, 1.5)
    max_raises_per_street: int = 3


@dataclass(frozen=True)
class PublicState:
    street: Street
    board: Tuple[str, ...]
    pot_bb: float
    stacks_bb: Tuple[float, float]
    street_committed_bb: Tuple[float, float]
    first_to_act: int
    to_act: int
    aggressor: int | None = None
    raise_count: int = 0
    history: Tuple[Action, ...] = ()
    street_complete: bool = False
    folded_player: int | None = None
    showdown: bool = False

    @property
    def terminal(self) -> bool:
        return self.folded_player is not None or self.showdown

    @property
    def opponent(self) -> int:
        return 1 - self.to_act


def initial_postflop_state(
    street: Street,
    board: Iterable[str],
    pot_bb: float,
    stacks_bb: Tuple[float, float],
    first_to_act: int,
) -> PublicState:
    required_board_cards = {Street.FLOP: 3, Street.TURN: 4, Street.RIVER: 5}
    if street not in required_board_cards:
        raise ValueError("This engine gate starts at flop, turn, or river.")
    normalized_board = tuple(board)
    if len(normalized_board) != required_board_cards[street]:
        raise ValueError(f"{street.value} requires {required_board_cards[street]} board cards.")
    if pot_bb <= 0 or min(stacks_bb) < 0 or first_to_act not in (0, 1):
        raise ValueError("Invalid initial public state.")
    return PublicState(
        street=street,
        board=normalized_board,
        pot_bb=pot_bb,
        stacks_bb=stacks_bb,
        street_committed_bb=(0.0, 0.0),
        first_to_act=first_to_act,
        to_act=first_to_act,
    )


def legal_actions(state: PublicState, config: GameConfig) -> Tuple[Action, ...]:
    if state.terminal or state.street_complete:
        return ()

    player = state.to_act
    opponent = 1 - player
    own_commitment = state.street_committed_bb[player]
    opponent_commitment = state.street_committed_bb[opponent]
    to_call = max(0.0, opponent_commitment - own_commitment)
    stack = state.stacks_bb[player]

    if to_call > 0:
        actions = [Action(ActionKind.FOLD)]
        if stack >= to_call:
            actions.append(Action(ActionKind.CALL, opponent_commitment))
        else:
            actions.append(Action(ActionKind.ALL_IN, own_commitment + stack))
        if state.raise_count < config.max_raises_per_street and stack > to_call:
            actions.extend(_sizing_actions(ActionKind.RAISE, state, config.postflop_raise_sizes))
        return _deduplicate(actions)

    actions = [Action(ActionKind.CHECK)]
    if stack > 0:
        actions.extend(_sizing_actions(ActionKind.BET, state, config.postflop_bet_sizes))
    return _deduplicate(actions)


def apply_action(state: PublicState, action: Action, config: GameConfig) -> PublicState:
    if action not in legal_actions(state, config):
        raise ValueError(f"Illegal action {action.label} for {state.street.value} state.")

    player = state.to_act
    opponent = 1 - player
    commitments = list(state.street_committed_bb)
    stacks = list(state.stacks_bb)
    history = state.history + (action,)

    if action.kind == ActionKind.FOLD:
        return _replace(state, history=history, folded_player=player)

    if action.kind in (ActionKind.BET, ActionKind.RAISE, ActionKind.CALL, ActionKind.ALL_IN):
        delta = action.target_commitment - commitments[player]
        if delta < -1e-9 or delta > stacks[player] + 1e-9:
            raise ValueError("Action commitment exceeds available stack.")
        commitments[player] = action.target_commitment
        stacks[player] = max(0.0, stacks[player] - delta)

    if action.kind == ActionKind.CHECK:
        previous_was_check = bool(state.history) and state.history[-1].kind == ActionKind.CHECK
        if state.aggressor is None and previous_was_check:
            return _replace(state, history=history, street_complete=True)
        return _replace(state, history=history, to_act=opponent)

    if action.kind == ActionKind.CALL:
        return _replace(
            state,
            history=history,
            stacks_bb=tuple(stacks),
            street_committed_bb=tuple(commitments),
            street_complete=True,
        )

    if action.kind == ActionKind.ALL_IN:
        if commitments[player] <= commitments[opponent]:
            # A shorter stack calls all-in. Uncalled chips return to the other
            # player, represented by matching both street commitments here.
            commitments[opponent] = commitments[player]
            return _replace(
                state,
                history=history,
                stacks_bb=tuple(stacks),
                street_committed_bb=tuple(commitments),
                street_complete=True,
            )
        return _replace(
            state,
            history=history,
            stacks_bb=tuple(stacks),
            street_committed_bb=tuple(commitments),
            to_act=opponent,
            aggressor=player,
            raise_count=state.raise_count + (1 if state.aggressor is not None else 0),
        )

    if action.kind in (ActionKind.BET, ActionKind.RAISE):
        return _replace(
            state,
            history=history,
            stacks_bb=tuple(stacks),
            street_committed_bb=tuple(commitments),
            to_act=opponent,
            aggressor=player,
            raise_count=state.raise_count + (1 if action.kind == ActionKind.RAISE else 0),
        )
    raise ValueError(f"Unhandled action {action.kind}.")


def advance_street(state: PublicState, next_board_card: str | None) -> PublicState:
    if not state.street_complete or state.terminal:
        raise ValueError("Only a completed non-terminal street can advance.")
    if state.street == Street.RIVER:
        return _replace(state, showdown=True)
    if next_board_card is None:
        raise ValueError("A board card is required before river.")
    return PublicState(
        street=state.street.next(),
        board=state.board + (next_board_card,),
        pot_bb=state.pot_bb + sum(state.street_committed_bb),
        stacks_bb=state.stacks_bb,
        street_committed_bb=(0.0, 0.0),
        first_to_act=state.first_to_act,
        to_act=state.first_to_act,
    )


def _sizing_actions(kind: ActionKind, state: PublicState, sizes: Tuple[float, ...]) -> list[Action]:
    player = state.to_act
    opponent = 1 - player
    own_commitment = state.street_committed_bb[player]
    opponent_commitment = state.street_committed_bb[opponent]
    all_in_target = own_commitment + state.stacks_bb[player]
    actions: list[Action] = []
    for fraction in sizes:
        target = state.pot_bb * fraction if kind == ActionKind.BET else opponent_commitment + state.pot_bb * fraction
        target = min(target, all_in_target)
        if target > own_commitment and (kind == ActionKind.BET or target > opponent_commitment):
            actions.append(Action(kind, round(target, 6), str(int(round(fraction * 100)))))
    if (
        all_in_target > own_commitment
        and (kind == ActionKind.BET or all_in_target > opponent_commitment)
        and all(action.target_commitment != round(all_in_target, 6) for action in actions)
    ):
        actions.append(Action(ActionKind.ALL_IN, round(all_in_target, 6), "allin"))
    return actions


def _deduplicate(actions: list[Action]) -> Tuple[Action, ...]:
    seen = set()
    unique = []
    for action in actions:
        key = (action.kind, round(action.target_commitment, 6))
        if key not in seen:
            unique.append(action)
            seen.add(key)
    return tuple(unique)


def _replace(state: PublicState, **changes: object) -> PublicState:
    values = {
        "street": state.street,
        "board": state.board,
        "pot_bb": state.pot_bb,
        "stacks_bb": state.stacks_bb,
        "street_committed_bb": state.street_committed_bb,
        "first_to_act": state.first_to_act,
        "to_act": state.to_act,
        "aggressor": state.aggressor,
        "raise_count": state.raise_count,
        "history": state.history,
        "street_complete": state.street_complete,
        "folded_player": state.folded_player,
        "showdown": state.showdown,
    }
    values.update(changes)
    return PublicState(**values)
