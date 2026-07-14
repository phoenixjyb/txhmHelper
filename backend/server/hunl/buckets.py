"""Versioned public-board and private-hand buckets for the Gate B flop abstraction."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable, Sequence

from solver_cfr import best_rank_seven, parse_cards

RANK_ORDER = "23456789TJQKA"
MADE_HAND_LABELS = (
    "high_card",
    "pair",
    "two_pair",
    "trips",
    "straight",
    "flush",
    "full_house",
    "quads",
    "straight_flush",
)


def board_texture_bucket(board: Iterable[str]) -> str:
    """Return a suit-isomorphic texture label for a flop, turn, or river board."""
    cards = tuple(board)
    if len(cards) not in (3, 4, 5):
        raise ValueError("Board texture buckets require flop, turn, or river cards.")
    ranks = [RANK_ORDER.index(card[0]) + 2 for card in cards]
    rank_counts = Counter(ranks)
    suits = Counter(card[1] for card in cards)
    paired = "trips" if 3 in rank_counts.values() else "paired" if 2 in rank_counts.values() else "unpaired"
    suit_shape = _suit_shape(sorted(suits.values(), reverse=True), len(cards))
    connectivity = _connectivity(ranks)
    high_cards = sum(rank >= 11 for rank in ranks)
    return f"n={len(cards)}|{paired}|{suit_shape}|{connectivity}|high={high_cards}"


def private_hand_bucket(hole_cards: Sequence[str], board: Sequence[str]) -> str:
    """Bucket private cards by rank pattern, current hand, draw class, and board relation.

    Hole-card ranks remain distinct (``AK`` versus ``Q9``), while suit identity
    is still abstracted through the draw class. This prevents strategically
    different unpaired high-card hands from sharing one information set on a
    dry flop without returning to exact suit-combo information sets.
    """
    if len(hole_cards) != 2:
        raise ValueError("Private hand buckets require exactly two hole cards.")
    cards = list(hole_cards) + list(board)
    if len(cards) not in (5, 6, 7):
        raise ValueError("Private hand buckets require a flop, turn, or river board.")
    parsed = parse_cards(cards)
    made_rank, _ = best_rank_seven(parsed)
    made = MADE_HAND_LABELS[made_rank]
    draw = _draw_bucket(cards, made_rank)
    relation = _hole_relation(hole_cards, board)
    return f"ranks={_hole_rank_profile(hole_cards)}|made={made}|draw={draw}|relation={relation}"


def _hole_rank_profile(hole_cards: Sequence[str]) -> str:
    """Return a suit-isomorphic, high-to-low two-card rank label."""
    return "".join(sorted((card[0] for card in hole_cards), key=RANK_ORDER.index, reverse=True))


def _suit_shape(counts: Sequence[int], card_count: int) -> str:
    highest = counts[0]
    if highest == card_count:
        return "monotone"
    if highest >= 3:
        return "three_tone"
    if highest == 2:
        return "two_tone"
    return "rainbow"


def _connectivity(ranks: Sequence[int]) -> str:
    unique = sorted(set(ranks))
    if 14 in unique:
        unique.append(1)
    best = 1
    for subset_size in range(2, min(5, len(unique)) + 1):
        for subset in combinations(unique, subset_size):
            if max(subset) - min(subset) <= 4:
                best = max(best, subset_size)
    return "connected" if best >= 3 else "semi_connected" if best == 2 else "disconnected"


def _draw_bucket(cards: Sequence[str], made_rank: int) -> str:
    suit_counts = Counter(card[1] for card in cards)
    flush_draw = max(suit_counts.values()) == 4 and made_rank < 5
    ranks = {RANK_ORDER.index(card[0]) + 2 for card in cards}
    if 14 in ranks:
        ranks.add(1)
    straight_draw = False
    for low in range(1, 11):
        if len(ranks & set(range(low, low + 5))) == 4 and made_rank < 4:
            straight_draw = True
            break
    if flush_draw and straight_draw:
        return "combo"
    if flush_draw:
        return "flush"
    if straight_draw:
        return "straight"
    return "none"


def _hole_relation(hole_cards: Sequence[str], board: Sequence[str]) -> str:
    hole_ranks = [RANK_ORDER.index(card[0]) + 2 for card in hole_cards]
    board_ranks = [RANK_ORDER.index(card[0]) + 2 for card in board]
    if hole_ranks[0] == hole_ranks[1]:
        return "pocket"
    shared = sorted(set(hole_ranks) & set(board_ranks), reverse=True)
    if not shared:
        return "unpaired"
    ordered_board = sorted(set(board_ranks), reverse=True)
    if shared[0] == ordered_board[0]:
        return "top_pair"
    if len(ordered_board) > 1 and shared[0] == ordered_board[1]:
        return "middle_pair"
    return "weak_pair"
