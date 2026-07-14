"""Canonical public-state keys and simple stack/pot buckets for HUNL v1."""
from __future__ import annotations

from typing import Iterable, Sequence

from .game import PublicState
from .buckets import board_texture_bucket

RANK_ORDER = "23456789TJQKA"
SUIT_SYMBOLS = "abcd"
POT_BUCKETS_BB = (2, 4, 8, 15, 25, 40, 60, 100, 160, 250, 400)
STACK_BUCKETS_BB = (5, 10, 20, 35, 50, 75, 100)


def canonical_board(board: Iterable[str]) -> str:
    """Suit-isomorphic board representation for a public information set."""
    ordered = sorted(board, key=lambda card: (-RANK_ORDER.index(card[0]), card[1]))
    suit_map: dict[str, str] = {}
    canonical = []
    for card in ordered:
        # Do not use setdefault here: its default expression is evaluated even
        # for an existing suit, which fails on a five-card board containing all
        # four suits followed by a duplicate suit.
        if card[1] not in suit_map:
            suit_map[card[1]] = SUIT_SYMBOLS[len(suit_map)]
        canonical.append(f"{card[0]}{suit_map[card[1]]}")
    return "".join(canonical)


def bucket(value: float, boundaries: Sequence[float]) -> float:
    for boundary in boundaries:
        if value <= boundary:
            return boundary
    return boundaries[-1]


def public_state_key(
    state: PublicState,
    abstraction_version: str,
    use_board_texture_buckets: bool = False,
) -> str:
    history = ",".join(action.label for action in state.history) or "root"
    stack_key = ",".join(str(bucket(stack, STACK_BUCKETS_BB)) for stack in state.stacks_bb)
    return "|".join(
        (
            abstraction_version,
            state.street.value,
            board_texture_bucket(state.board) if use_board_texture_buckets else canonical_board(state.board),
            f"pot={bucket(state.pot_bb, POT_BUCKETS_BB)}",
            f"stacks={stack_key}",
            f"to_act={state.to_act}",
            f"raises={state.raise_count}",
            history,
        )
    )
