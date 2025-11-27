"""
Monte Carlo CFR solver for heads-up no-limit Hold'em with a simplified bet tree.

Supports all streets by sampling unknown cards to the river each iteration.
Action tree (single bet size, pot-fraction):
    P0 acts first: check / bet
      if bet -> P1: fold / call
      if check -> P1: check / bet
           if bet -> P0: fold / call

Assumptions:
- Single bet size = pot * bet_frac (capped by effective stack / pot).
- No raises beyond one bet.
- Stack assumed sufficient for the bet size after capping.

This is approximate but runs real CFR updates with sampled opponent hands and runouts.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

RANKS = "23456789TJQKA"
SUITS = "cdhs"


def card_to_int(card: str) -> Tuple[int, int]:
    return RANKS.index(card[0]), SUITS.index(card[1])


def parse_cards(cards: List[str]) -> List[Tuple[int, int]]:
    return [card_to_int(c) for c in cards]


def hand_rank_five(cards: List[Tuple[int, int]]) -> Tuple[int, List[int]]:
    ranks = sorted([r for r, _ in cards], reverse=True)
    suits = [s for _, s in cards]
    counts = {r: ranks.count(r) for r in set(ranks)}
    is_flush = len(set(suits)) == 1
    distinct = sorted(set(ranks), reverse=True)
    straight_high = None
    if len(distinct) >= 5:
        for i in range(len(distinct) - 4):
            window = distinct[i : i + 5]
            if window[0] - window[-1] == 4:
                straight_high = window[0]
                break
        if set([12, 3, 2, 1, 0]).issubset(set(ranks)):
            straight_high = 3
    if is_flush and straight_high is not None:
        return (8, [straight_high])
    if 4 in counts.values():
        four = max(k for k, v in counts.items() if v == 4)
        kicker = max(k for k in ranks if k != four)
        return (7, [four, kicker])
    if sorted(counts.values(), reverse=True)[:2] == [3, 2]:
        trips = max(k for k, v in counts.items() if v == 3)
        pair = max(k for k, v in counts.items() if v == 2)
        return (6, [trips, pair])
    if is_flush:
        return (5, ranks)
    if straight_high is not None:
        return (4, [straight_high])
    if 3 in counts.values():
        trips = max(k for k, v in counts.items() if v == 3)
        kickers = [k for k in ranks if k != trips][:2]
        return (3, [trips] + kickers)
    pairs = sorted([k for k, v in counts.items() if v == 2], reverse=True)
    if len(pairs) >= 2:
        kicker = max(k for k in ranks if k not in pairs[:2])
        return (2, pairs[:2] + [kicker])
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = [k for k in ranks if k != pair][:3]
        return (1, [pair] + kickers)
    return (0, ranks)


def best_rank_seven(cards7: List[Tuple[int, int]]) -> Tuple[int, List[int]]:
    best = (-1, [])
    for combo in itertools.combinations(cards7, 5):
        rank = hand_rank_five(list(combo))
        if rank > best:
            best = rank
    return best


def winner(hero: List[Tuple[int, int]], villain: List[Tuple[int, int]], board: List[Tuple[int, int]]) -> int:
    hero_rank = best_rank_seven(hero + board)
    vill_rank = best_rank_seven(villain + board)
    if hero_rank > vill_rank:
        return 1
    if hero_rank < vill_rank:
        return -1
    return 0


ACTION_ROOT = ["check", "bet"]
ACTION_VS_BET = ["fold", "call"]


@dataclass
class Node:
    info: str
    actions: List[str]
    regret: Dict[str, float]
    strategy_sum: Dict[str, float]

    def __init__(self, info: str, actions: List[str]):
        self.info = info
        self.actions = actions
        self.regret = {a: 0.0 for a in actions}
        self.strategy_sum = {a: 0.0 for a in actions}

    def get_strategy(self, reach: float) -> Dict[str, float]:
        positives = [max(r, 0.0) for r in self.regret.values()]
        total = sum(positives)
        if total > 0:
            strat = {a: max(self.regret[a], 0.0) / total for a in self.actions}
        else:
            strat = {a: 1.0 / len(self.actions) for a in self.actions}
        for a in self.actions:
            self.strategy_sum[a] += reach * strat[a]
        return strat

    def avg_strategy(self) -> Dict[str, float]:
        total = sum(self.strategy_sum.values())
        if total == 0:
            return {a: 1.0 / len(self.actions) for a in self.actions}
        return {a: self.strategy_sum[a] / total for a in self.actions}


class StreetCFR:
    def __init__(self, pot: float, bet_frac: float = 1.0):
        self.pot = pot
        self.bet_frac = bet_frac
        self.nodes: Dict[str, Node] = {}

    def cfr(
        self,
        hero_hand: List[Tuple[int, int]],
        opp_hand: List[Tuple[int, int]],
        board: List[Tuple[int, int]],
        p0: float,
        p1: float,
        history: str = "",
    ) -> float:
        terminal, util = self._terminal_utility(history, hero_hand, opp_hand, board)
        if terminal:
            return util

        player = 0 if (len(history) % 2 == 0) else 1  # hero first
        info = self._info_key(player, hero_hand if player == 0 else opp_hand, board, history)
        actions = self._legal_actions(history)
        node = self.nodes.get(info)
        if node is None:
            node = Node(info, actions)
            self.nodes[info] = node

        strategy = node.get_strategy(p0 if player == 0 else p1)
        util_child = {}
        node_util = 0.0
        for a in actions:
            next_hist = history + a[0]
            if player == 0:
                util_child[a] = self.cfr(hero_hand, opp_hand, board, p0 * strategy[a], p1, next_hist)
            else:
                util_child[a] = self.cfr(hero_hand, opp_hand, board, p0, p1 * strategy[a], next_hist)
            node_util += strategy[a] * util_child[a]

        for a in actions:
            regret = util_child[a] - node_util
            if player == 0:
                node.regret[a] += p1 * regret
            else:
                node.regret[a] += p0 * regret
        return node_util

    def _info_key(self, player: int, hand: List[Tuple[int, int]], board: List[Tuple[int, int]], history: str) -> str:
        rank = best_rank_seven(hand + board)
        return f"P{player}|{rank[0]}|{rank[1]}|{history}"

    def _legal_actions(self, history: str) -> List[str]:
        if history == "":
            return ACTION_ROOT
        if history == "c":  # P1 after P0 check
            return ACTION_ROOT
        if history in ("b", "cb"):  # facing a bet
            return ACTION_VS_BET
        return ACTION_ROOT

    def _terminal_utility(
        self,
        history: str,
        hero_hand: List[Tuple[int, int]],
        opp_hand: List[Tuple[int, int]],
        board: List[Tuple[int, int]],
    ) -> Tuple[bool, float]:
        pot = self.pot
        bet = pot * self.bet_frac
        if history in ("bc", "cbc"):
            win = winner(hero_hand, opp_hand, board)
            return True, win * (pot + bet)
        if history in ("bf", "cbf"):
            last_bet_by_hero = history == "bf"
            return True, pot if last_bet_by_hero else -pot
        if history == "cc":
            win = winner(hero_hand, opp_hand, board)
            return True, win * pot
        return False, 0.0

    def solve(
        self,
        hero_hand: List[str],
        board: List[str],
        remaining_cards: List[str],
        iterations: int = 3000,
        sample_opp: int = 4000,
    ) -> Dict[str, float]:
        hero = parse_cards(hero_hand)
        board_c = parse_cards(board)
        deck = [(r, s) for r in range(13) for s in range(4)]
        used = set(hero + board_c)
        deck = [c for c in deck if c not in used]

        for _ in range(iterations):
            opp = random.choice(list(itertools.combinations(deck, 2)))
            # sample a complete board
            needed = 5 - len(board_c)
            runout_cards = []
            if needed > 0:
                pool = [c for c in deck if c not in opp]
                runout_cards = random.sample(pool, needed)
            full_board = board_c + runout_cards
            self.cfr(hero, list(opp), full_board, p0=1.0, p1=1.0, history="")

        root = self.nodes.get(self._info_key(0, hero, board_c, ""))
        if not root:
            return {}
        return root.avg_strategy()


def solve_cfr(stage: str, hole: List[str], board: List[str], pot: float, effective_stack: float, bet_frac: float) -> Dict[str, float]:
    if len(hole) != 2:
        raise ValueError("Hole cards must be length 2.")
    if len(board) > 5:
        raise ValueError("Board cannot exceed 5 cards.")
    pot = max(pot, 0.1)
    bet_frac = min(bet_frac, effective_stack / pot if pot > 0 else 1.0)
    solver = StreetCFR(pot=pot, bet_frac=bet_frac)
    remaining_cards = []
    return solver.solve(hole, board, remaining_cards)
