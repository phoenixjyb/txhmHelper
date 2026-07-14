"""CUDA-capable batched seven-card terminal evaluator.

Cards are integer tensors shaped ``[batch, 7, 2]``. Rank is 2..14 and suit is
0..3. The implementation evaluates all 21 five-card subsets with tensor
operations and returns a lexicographically encoded hand score. It is designed
as the terminal-payoff backend for external-sampling CFR, not as a neural model.
"""
from __future__ import annotations

from itertools import combinations
from typing import Tuple


def evaluate_seven(cards):
    """Return one comparable integer score per seven-card hand on the input device."""
    torch = _torch()
    if cards.ndim != 3 or cards.shape[1:] != (7, 2):
        raise ValueError("Expected cards shaped [batch, 7, 2].")
    cards = cards.to(dtype=torch.long)
    scores = [_evaluate_five(cards[:, subset, :], torch) for subset in combinations(range(7), 5)]
    return torch.stack(scores, dim=1).max(dim=1).values


def showdown_equity(hero_cards, villain_cards):
    """Return terminal equity (1 win, 0.5 tie, 0 loss) for each batched showdown."""
    torch = _torch()
    hero_score = evaluate_seven(hero_cards)
    villain_score = evaluate_seven(villain_cards)
    return torch.where(
        hero_score > villain_score,
        torch.ones_like(hero_score, dtype=torch.float32),
        torch.where(hero_score == villain_score, torch.full_like(hero_score, 0.5, dtype=torch.float32), torch.zeros_like(hero_score, dtype=torch.float32)),
    )


def _evaluate_five(cards, torch):
    ranks = cards[:, :, 0]
    suits = cards[:, :, 1]
    sorted_ranks = ranks.sort(dim=1, descending=True).values
    rank_values = torch.arange(2, 15, device=cards.device, dtype=torch.long).view(1, 13)
    counts = (ranks.unsqueeze(-1) == rank_values.unsqueeze(1)).sum(dim=1)
    presence = counts > 0

    flush = suits.eq(suits[:, :1]).all(dim=1)
    straight_high = _straight_high(presence, torch)
    pair_ranks = _sorted_rank_list(counts == 2, rank_values, torch)
    trip_ranks = _sorted_rank_list(counts == 3, rank_values, torch)
    quad_ranks = _sorted_rank_list(counts == 4, rank_values, torch)
    single_ranks = _sorted_rank_list(counts == 1, rank_values, torch)

    pair = pair_ranks[:, 0] > 0
    two_pair = pair_ranks[:, 1] > 0
    trips = trip_ranks[:, 0] > 0
    quads = quad_ranks[:, 0] > 0
    straight = straight_high > 0
    full_house = trips & pair
    straight_flush = straight & flush

    score = _score(0, [sorted_ranks[:, index] for index in range(5)], torch)
    score = torch.where(pair, _score(1, [pair_ranks[:, 0], single_ranks[:, 0], single_ranks[:, 1], single_ranks[:, 2]], torch), score)
    score = torch.where(two_pair, _score(2, [pair_ranks[:, 0], pair_ranks[:, 1], single_ranks[:, 0]], torch), score)
    score = torch.where(trips, _score(3, [trip_ranks[:, 0], single_ranks[:, 0], single_ranks[:, 1]], torch), score)
    score = torch.where(straight, _score(4, [straight_high], torch), score)
    score = torch.where(flush, _score(5, [sorted_ranks[:, index] for index in range(5)], torch), score)
    score = torch.where(full_house, _score(6, [trip_ranks[:, 0], pair_ranks[:, 0]], torch), score)
    score = torch.where(quads, _score(7, [quad_ranks[:, 0], single_ranks[:, 0]], torch), score)
    return torch.where(straight_flush, _score(8, [straight_high], torch), score)


def _straight_high(presence, torch):
    result = torch.zeros(presence.shape[0], device=presence.device, dtype=torch.long)
    for high in range(6, 15):
        is_straight = presence[:, high - 6 : high - 1].all(dim=1)
        result = torch.where(is_straight, torch.full_like(result, high), result)
    wheel = presence[:, 12] & presence[:, 0] & presence[:, 1] & presence[:, 2] & presence[:, 3]
    return torch.maximum(result, torch.where(wheel, torch.full_like(result, 5), torch.zeros_like(result)))


def _sorted_rank_list(mask, rank_values, torch):
    return torch.where(mask, rank_values.expand(mask.shape[0], -1), torch.zeros_like(rank_values).expand(mask.shape[0], -1)).sort(dim=1, descending=True).values


def _score(category: int, kickers, torch):
    result = torch.full_like(kickers[0], category, dtype=torch.long)
    zero = torch.zeros_like(result)
    for index in range(5):
        result = result * 15 + (kickers[index] if index < len(kickers) else zero)
    return result


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch with CUDA support is required for the torch evaluator.") from exc
    return torch
