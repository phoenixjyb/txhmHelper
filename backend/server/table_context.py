"""Translate exact heads-up table actions into the bounded solver's action labels.

The deployed CFR+ game uses pot-relative actions such as ``bet_50`` and
``raise_75``.  The mobile app records the more useful real-table form:
player, action kind, and total commitment on the current street.  This module
keeps the original amount auditable while deriving a reproducible one-percent
pot-relative label for the existing solver.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


EPSILON = 1e-6


@dataclass(frozen=True)
class TableAction:
    player: Literal["hero", "villain"]
    type: Literal["check", "bet", "call", "raise", "fold", "all_in"]
    amount_to: float | None = None


@dataclass(frozen=True)
class NormalizedTableContext:
    action_history: list[str]
    bet_sizing: list[float]
    raise_sizing: list[float]


def normalize_table_context(
    *,
    pot_before_street: float,
    effective_stack: float,
    hero_position: Literal["oop", "ip"],
    actions: Sequence[TableAction],
    bet_sizing: Sequence[float],
    raise_sizing: Sequence[float],
) -> NormalizedTableContext:
    """Validate a user-recorded heads-up line and derive solver action labels.

    ``amount_to`` is always the player's *total* commitment on the current
    street.  The bounded game accepts a single decision street only, so prior
    street chips belong in ``pot_before_street`` and are not replayed here.
    """
    if pot_before_street <= 0:
        raise ValueError("pot_before_street must be positive for postflop solving.")
    if effective_stack <= 0:
        raise ValueError("effective_stack must be positive.")
    if len(actions) > 4:
        raise ValueError("At most four actions can be mapped in the bounded solver.")

    first_player = 0 if hero_position == "oop" else 1
    contributions = [0.0, 0.0]
    history: list[str] = []
    normalized_bets = list(bet_sizing)
    normalized_raises = list(raise_sizing)

    for index, action in enumerate(actions):
        actor = 0 if action.player == "hero" else 1
        expected_actor = (first_player + index) % 2
        if actor != expected_actor:
            raise ValueError("Table actions are not in the expected heads-up turn order.")

        opponent = 1 - actor
        to_call = max(0.0, contributions[opponent] - contributions[actor])
        amount = action.amount_to
        if action.type == "check":
            if to_call > EPSILON:
                raise ValueError("A player facing a bet must call, raise, or fold.")
            label = "check"
        elif action.type == "call":
            if to_call <= EPSILON:
                raise ValueError("Nothing to call; record a check instead.")
            contributions[actor] = contributions[opponent]
            label = "call"
        elif action.type == "fold":
            if to_call <= EPSILON:
                raise ValueError("A player may fold only when facing a bet in this solver.")
            label = "fold"
        else:
            target = effective_stack if action.type == "all_in" else _valid_target(amount, effective_stack)
            if target <= contributions[actor] + EPSILON:
                raise ValueError("The action must add chips on this street.")
            if target > effective_stack + EPSILON:
                raise ValueError("The action exceeds the effective stack.")

            if action.type == "all_in" and abs(target - contributions[opponent]) <= EPSILON:
                contributions[actor] = contributions[opponent]
                label = "call"
            elif to_call <= EPSILON:
                fraction = _normalized_fraction(target / pot_before_street)
                normalized_bets.append(fraction)
                contributions[actor] = target
                label = _label("bet", fraction)
            else:
                if target <= contributions[opponent] + EPSILON:
                    raise ValueError("A raise must be above the opponent's current commitment.")
                fraction = _normalized_fraction((target - contributions[opponent]) / pot_before_street)
                normalized_raises.append(fraction)
                contributions[actor] = target
                label = _label("raise", fraction)
        history.append(label)

    _validate_bounded_history(history, hero_position, normalized_bets, normalized_raises, pot_before_street, effective_stack)
    return NormalizedTableContext(
        action_history=history,
        bet_sizing=_normalized_sizes(normalized_bets),
        raise_sizing=_normalized_sizes(normalized_raises),
    )


def _validate_bounded_history(
    history: Sequence[str],
    hero_position: str,
    bet_sizing: Sequence[float],
    raise_sizing: Sequence[float],
    pot_before_street: float,
    effective_stack: float,
) -> None:
    # Reuse the solver's actual transition rules so this adapter cannot quietly
    # accept a line that the CFR+ job would later reject.
    from solver_v2 import HeadsUpPostflopCfr

    solver = HeadsUpPostflopCfr(
        pot=pot_before_street,
        effective_stack=effective_stack,
        bet_sizes=bet_sizing,
        raise_sizes=raise_sizing,
    )
    first_player = 0 if hero_position == "oop" else 1
    state = solver._replay_history(tuple(history), first_player)
    if solver._is_terminal(state.history):
        raise ValueError("The recorded street is complete; advance the street before requesting a decision.")
    if state.actor != 0:
        raise ValueError("The recorded line leaves the opponent to act; select Hero when it is Hero's turn.")


def _valid_target(amount: float | None, effective_stack: float) -> float:
    if amount is None or amount <= 0:
        raise ValueError("Bet and raise actions require a positive amount_to value.")
    if amount > effective_stack + EPSILON:
        raise ValueError("The action exceeds the effective stack.")
    return amount


def _normalized_fraction(value: float) -> float:
    if value <= 0:
        raise ValueError("Action sizing must be positive.")
    return round(value, 2)


def _normalized_sizes(values: Sequence[float]) -> list[float]:
    return sorted({round(value, 2) for value in values if value > 0})


def _label(kind: str, fraction: float) -> str:
    return f"{kind}_{int(round(fraction * 100))}"
