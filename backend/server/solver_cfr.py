"""Chance-sampled CFR for a heads-up, one-street no-limit Hold'em abstraction.

The solver models a decision at the supplied street. Unknown cards are sampled
to the river for showdown evaluation; they are never included in an information
set. This is important: a player cannot base a strategy on future board cards.

Action tree:
    first player: check or one of the allowed bet sizes
      bet -> second player: fold or call
    check -> second player: check or one of the allowed bet sizes
      bet -> first player: fold or call

It is a real two-player zero-sum CFR implementation for this deliberately small
game tree. It is not a full-ring, multi-street production poker solver: there
are no raises, range editor, or post-action street transitions yet.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

RANKS = "23456789TJQKA"
SUITS = "cdhs"
CardValue = Tuple[int, int]
History = Tuple[str, ...]


def card_to_int(card: str) -> CardValue:
    if len(card) != 2 or card[0] not in RANKS or card[1] not in SUITS:
        raise ValueError(f"Invalid card: {card!r}")
    return RANKS.index(card[0]), SUITS.index(card[1])


def parse_cards(cards: Iterable[str]) -> List[CardValue]:
    parsed = [card_to_int(card) for card in cards]
    if len(set(parsed)) != len(parsed):
        raise ValueError("Cards must not contain duplicates.")
    return parsed


def hand_rank_five(cards: Sequence[CardValue]) -> Tuple[int, List[int]]:
    ranks = sorted((rank for rank, _ in cards), reverse=True)
    suits = [suit for _, suit in cards]
    counts = {rank: ranks.count(rank) for rank in set(ranks)}
    is_flush = len(set(suits)) == 1
    distinct = sorted(set(ranks), reverse=True)
    straight_high = None
    if len(distinct) >= 5:
        for index in range(len(distinct) - 4):
            window = distinct[index : index + 5]
            if window[0] - window[-1] == 4:
                straight_high = window[0]
                break
        if {12, 3, 2, 1, 0}.issubset(ranks):
            straight_high = 3
    if is_flush and straight_high is not None:
        return 8, [straight_high]
    if 4 in counts.values():
        four = max(rank for rank, count in counts.items() if count == 4)
        return 7, [four, max(rank for rank in ranks if rank != four)]
    if sorted(counts.values(), reverse=True)[:2] == [3, 2]:
        trips = max(rank for rank, count in counts.items() if count == 3)
        pair = max(rank for rank, count in counts.items() if count == 2)
        return 6, [trips, pair]
    if is_flush:
        return 5, ranks
    if straight_high is not None:
        return 4, [straight_high]
    if 3 in counts.values():
        trips = max(rank for rank, count in counts.items() if count == 3)
        kickers = [rank for rank in ranks if rank != trips][:2]
        return 3, [trips] + kickers
    pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
    if len(pairs) >= 2:
        kicker = max(rank for rank in ranks if rank not in pairs[:2])
        return 2, pairs[:2] + [kicker]
    if pairs:
        pair = pairs[0]
        kickers = [rank for rank in ranks if rank != pair][:3]
        return 1, [pair] + kickers
    return 0, ranks


def best_rank_seven(cards: Sequence[CardValue]) -> Tuple[int, List[int]]:
    if len(cards) < 5:
        raise ValueError("At least five cards are required to evaluate a hand.")
    return max(hand_rank_five(combo) for combo in itertools.combinations(cards, 5))


def winner(hero: Sequence[CardValue], villain: Sequence[CardValue], board: Sequence[CardValue]) -> int:
    hero_rank = best_rank_seven(list(hero) + list(board))
    villain_rank = best_rank_seven(list(villain) + list(board))
    return (hero_rank > villain_rank) - (hero_rank < villain_rank)


def _card_label(card: CardValue) -> str:
    return f"{RANKS[card[0]]}{SUITS[card[1]]}"


def _bet_action(fraction: float) -> str:
    return f"bet_{int(round(fraction * 100))}"


def _bet_fraction(action: str) -> float:
    if not action.startswith("bet_"):
        raise ValueError(f"Not a bet action: {action}")
    return int(action.removeprefix("bet_")) / 100.0


@dataclass
class Node:
    actions: Tuple[str, ...]
    regret: Dict[str, float] = field(init=False)
    strategy_sum: Dict[str, float] = field(init=False)

    def __post_init__(self) -> None:
        self.regret = {action: 0.0 for action in self.actions}
        self.strategy_sum = {action: 0.0 for action in self.actions}

    def strategy(self, reach_probability: float) -> Dict[str, float]:
        positive_regrets = {action: max(0.0, self.regret[action]) for action in self.actions}
        total = sum(positive_regrets.values())
        if total == 0:
            current = {action: 1.0 / len(self.actions) for action in self.actions}
        else:
            current = {action: positive_regrets[action] / total for action in self.actions}
        for action, probability in current.items():
            self.strategy_sum[action] += reach_probability * probability
        return current

    def average_strategy(self) -> Dict[str, float]:
        total = sum(self.strategy_sum.values())
        if total == 0:
            return {action: 1.0 / len(self.actions) for action in self.actions}
        return {action: self.strategy_sum[action] / total for action in self.actions}


class StreetCFR:
    def __init__(self, pot: float, effective_stack: float, bet_sizes: Sequence[float]) -> None:
        self.pot = pot
        self.effective_stack = effective_stack
        self.bet_sizes = tuple(sorted({round(size, 2) for size in bet_sizes if size > 0}))
        if not self.bet_sizes:
            raise ValueError("At least one positive bet size is required.")
        self.nodes: Dict[str, Node] = {}

    def solve(
        self,
        hero_hand: Sequence[str],
        public_board: Sequence[str],
        iterations: int = 3_000,
        rng: random.Random | None = None,
    ) -> Dict[str, float]:
        hero = parse_cards(hero_hand)
        board = parse_cards(public_board)
        if len(hero) != 2:
            raise ValueError("Hole cards must contain exactly two cards.")
        if len(board) > 5:
            raise ValueError("Board cannot contain more than five cards.")
        if set(hero) & set(board):
            raise ValueError("Hole and board cards must not overlap.")
        if iterations < 1:
            raise ValueError("Iterations must be positive.")

        generator = rng or random.Random()
        deck = [(rank, suit) for rank in range(13) for suit in range(4)]
        deck = [card for card in deck if card not in set(hero) | set(board)]
        for _ in range(iterations):
            villain = generator.sample(deck, 2)
            runout_pool = [card for card in deck if card not in villain]
            final_board = list(board) + generator.sample(runout_pool, 5 - len(board))
            self._cfr(
                hero=hero,
                villain=villain,
                public_board=board,
                final_board=final_board,
                hero_reach=1.0,
                villain_reach=1.0,
                history=(),
            )

        root = self.nodes[self._info_key(0, hero, board, ())]
        return root.average_strategy()

    def _cfr(
        self,
        hero: Sequence[CardValue],
        villain: Sequence[CardValue],
        public_board: Sequence[CardValue],
        final_board: Sequence[CardValue],
        hero_reach: float,
        villain_reach: float,
        history: History,
    ) -> float:
        terminal_value = self._terminal_utility(history, hero, villain, final_board)
        if terminal_value is not None:
            return terminal_value

        player = self._acting_player(history)
        private_hand = hero if player == 0 else villain
        info_key = self._info_key(player, private_hand, public_board, history)
        actions = self._legal_actions(history)
        node = self.nodes.setdefault(info_key, Node(actions))
        strategy = node.strategy(hero_reach if player == 0 else villain_reach)

        action_utilities: Dict[str, float] = {}
        node_utility = 0.0
        for action in actions:
            next_history = history + (action,)
            if player == 0:
                utility = self._cfr(
                    hero, villain, public_board, final_board,
                    hero_reach * strategy[action], villain_reach, next_history,
                )
            else:
                utility = self._cfr(
                    hero, villain, public_board, final_board,
                    hero_reach, villain_reach * strategy[action], next_history,
                )
            action_utilities[action] = utility
            node_utility += strategy[action] * utility

        counterfactual_reach = villain_reach if player == 0 else hero_reach
        for action, utility in action_utilities.items():
            # _cfr returns Hero's payoff. The opponent therefore regrets the
            # inverse payoff in this zero-sum game.
            regret = utility - node_utility if player == 0 else node_utility - utility
            node.regret[action] += counterfactual_reach * regret
        return node_utility

    def _info_key(
        self,
        player: int,
        private_hand: Sequence[CardValue],
        public_board: Sequence[CardValue],
        history: History,
    ) -> str:
        private_key = ",".join(sorted(_card_label(card) for card in private_hand))
        board_key = ",".join(_card_label(card) for card in public_board)
        history_key = ",".join(history) or "root"
        return f"P{player}|{private_key}|{board_key}|{history_key}"

    def _acting_player(self, history: History) -> int:
        if history in ((), ("check",)):
            return 0 if not history else 1
        if len(history) == 1 and history[0].startswith("bet_"):
            return 1
        if len(history) == 2 and history[0] == "check" and history[1].startswith("bet_"):
            return 0
        raise ValueError(f"Terminal history reached unexpectedly: {history}")

    def _legal_actions(self, history: History) -> Tuple[str, ...]:
        if history in ((), ("check",)):
            return ("check",) + tuple(_bet_action(size) for size in self.bet_sizes)
        if history and history[-1].startswith("bet_"):
            return "fold", "call"
        raise ValueError(f"No legal actions for history: {history}")

    def _terminal_utility(
        self,
        history: History,
        hero: Sequence[CardValue],
        villain: Sequence[CardValue],
        final_board: Sequence[CardValue],
    ) -> float | None:
        if history == ("check", "check"):
            return winner(hero, villain, final_board) * (self.pot / 2.0)

        if history[-1:] == ("fold",):
            # The bettor wins the opponent's half of the pot. The prior pot
            # contributions are sunk at this one-street decision point.
            bettor_is_hero = history[0].startswith("bet_")
            return self.pot / 2.0 if bettor_is_hero else -self.pot / 2.0

        if history[-1:] == ("call",):
            bet_action = history[0] if history[0].startswith("bet_") else history[1]
            wager = min(self.pot * _bet_fraction(bet_action), self.effective_stack)
            return winner(hero, villain, final_board) * (self.pot / 2.0 + wager)
        return None


def solve_cfr(
    stage: str,
    hole: List[str],
    board: List[str],
    pot: float,
    effective_stack: float,
    bet_sizes: Sequence[float] = (0.33, 0.5, 1.0),
    iterations: int = 3_000,
) -> Dict[str, float]:
    expected_board_cards = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
    normalized_stage = stage.lower()
    if normalized_stage not in expected_board_cards:
        raise ValueError(f"Unsupported stage: {stage}")
    if len(board) != expected_board_cards[normalized_stage]:
        raise ValueError(f"{normalized_stage} requires {expected_board_cards[normalized_stage]} board cards.")
    if pot <= 0 or effective_stack <= 0:
        raise ValueError("Pot and effective stack must be positive.")
    return StreetCFR(pot, effective_stack, bet_sizes).solve(hole, board, iterations)
