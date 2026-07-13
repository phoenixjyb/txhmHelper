"""Range-aware CFR+ for a bounded heads-up postflop Hold'em abstraction.

The game starts at a supplied street and samples unknown runouts to river. It
supports position, weighted villain ranges, bet sizes, a capped raise response,
and optional rake. It intentionally does not yet model a new decision tree on
later streets; those cards are sampled only for showdown value.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from solver_cfr import CardValue, parse_cards, winner

History = Tuple[str, ...]


@dataclass(frozen=True)
class WeightedCombo:
    cards: Tuple[str, str]
    weight: float


@dataclass(frozen=True)
class ActionState:
    history: History
    contributions: Tuple[float, float]
    first_player: int

    @property
    def actor(self) -> int:
        return (self.first_player + len(self.history)) % 2


@dataclass
class CfrNode:
    actions: Tuple[str, ...]

    def __post_init__(self) -> None:
        self.regret = {action: 0.0 for action in self.actions}
        self.strategy_sum = {action: 0.0 for action in self.actions}

    def strategy(self, reach: float) -> Dict[str, float]:
        positives = {action: max(0.0, self.regret[action]) for action in self.actions}
        normalizer = sum(positives.values())
        current = (
            {action: positives[action] / normalizer for action in self.actions}
            if normalizer > 0
            else {action: 1.0 / len(self.actions) for action in self.actions}
        )
        for action, probability in current.items():
            self.strategy_sum[action] += reach * probability
        return current

    def average_strategy(self) -> Dict[str, float]:
        normalizer = sum(self.strategy_sum.values())
        if normalizer == 0:
            return {action: 1.0 / len(self.actions) for action in self.actions}
        return {action: value / normalizer for action, value in self.strategy_sum.items()}


@dataclass(frozen=True)
class SolverResult:
    strategy: Dict[str, float]
    iterations: int
    node_count: int
    model: str = "heads-up-postflop-cfr-plus-v1"


class HeadsUpPostflopCfr:
    def __init__(
        self,
        pot: float,
        effective_stack: float,
        bet_sizes: Sequence[float],
        raise_sizes: Sequence[float],
        raise_cap: int = 1,
        rake_pct: float = 0.0,
        rake_cap: float = 0.0,
    ) -> None:
        self.pot = pot
        self.effective_stack = effective_stack
        self.bet_sizes = self._valid_sizes(bet_sizes, "bet")
        self.raise_sizes = self._valid_sizes(raise_sizes, "raise")
        self.raise_cap = raise_cap
        self.rake_pct = rake_pct
        self.rake_cap = rake_cap
        self.nodes: Dict[str, CfrNode] = {}

    def solve(
        self,
        hero_hand: Sequence[str],
        public_board: Sequence[str],
        hero_position: str,
        action_history: Sequence[str],
        villain_range: Sequence[WeightedCombo] | None,
        iterations: int,
        rng: random.Random | None = None,
    ) -> SolverResult:
        hero = parse_cards(hero_hand)
        board = parse_cards(public_board)
        if len(hero) != 2:
            raise ValueError("Hero must have exactly two hole cards.")
        if len(board) not in (3, 4, 5):
            raise ValueError("The v1 solver supports flop, turn, and river only.")
        if set(hero) & set(board):
            raise ValueError("Hero and board cards must not overlap.")
        if hero_position not in ("oop", "ip"):
            raise ValueError("hero_position must be 'oop' or 'ip'.")
        if iterations < 100:
            raise ValueError("iterations must be at least 100.")

        first_player = 0 if hero_position == "oop" else 1
        initial = self._replay_history(tuple(action_history), first_player)
        if self._is_terminal(initial.history):
            raise ValueError("Action history is already terminal.")
        if initial.actor != 0:
            raise ValueError("v1 solve requires Hero to be the next player to act.")

        generator = rng or random.Random()
        deck = [(rank, suit) for rank in range(13) for suit in range(4)]
        remaining = [card for card in deck if card not in set(hero) | set(board)]
        range_combos = self._prepare_range(villain_range, set(hero) | set(board))

        for _ in range(iterations):
            villain = self._sample_villain(remaining, range_combos, generator)
            runout_pool = [card for card in remaining if card not in villain]
            final_board = list(board) + generator.sample(runout_pool, 5 - len(board))
            self._cfr(
                hero=hero,
                villain=villain,
                public_board=board,
                final_board=final_board,
                state=initial,
                hero_reach=1.0,
                villain_reach=1.0,
            )

        root = self.nodes[self._info_key(0, hero, board, initial)]
        return SolverResult(root.average_strategy(), iterations, len(self.nodes))

    def _cfr(
        self,
        hero: Sequence[CardValue],
        villain: Sequence[CardValue],
        public_board: Sequence[CardValue],
        final_board: Sequence[CardValue],
        state: ActionState,
        hero_reach: float,
        villain_reach: float,
    ) -> float:
        utility = self._terminal_utility(state, hero, villain, final_board)
        if utility is not None:
            return utility

        player = state.actor
        private_hand = hero if player == 0 else villain
        actions = self._legal_actions(state)
        key = self._info_key(player, private_hand, public_board, state)
        node = self.nodes.setdefault(key, CfrNode(actions))
        strategy = node.strategy(hero_reach if player == 0 else villain_reach)

        action_utilities: Dict[str, float] = {}
        node_utility = 0.0
        for action in actions:
            child = self._apply(state, action)
            if player == 0:
                value = self._cfr(hero, villain, public_board, final_board, child, hero_reach * strategy[action], villain_reach)
            else:
                value = self._cfr(hero, villain, public_board, final_board, child, hero_reach, villain_reach * strategy[action])
            action_utilities[action] = value
            node_utility += strategy[action] * value

        counterfactual_reach = villain_reach if player == 0 else hero_reach
        for action, value in action_utilities.items():
            regret = value - node_utility if player == 0 else node_utility - value
            # CFR+ discards negative cumulative regrets.
            node.regret[action] = max(0.0, node.regret[action] + counterfactual_reach * regret)
        return node_utility

    def _replay_history(self, history: History, first_player: int) -> ActionState:
        state = ActionState((), (0.0, 0.0), first_player)
        for action in history:
            if self._is_terminal(state.history):
                raise ValueError("Action history continues after a terminal action.")
            if action not in self._legal_actions(state):
                raise ValueError(f"Illegal action in history: {action}")
            state = self._apply(state, action)
        return state

    def _legal_actions(self, state: ActionState) -> Tuple[str, ...]:
        history = state.history
        if not history or history == ("check",):
            return ("check",) + self._sizing_actions("bet", state)
        if history[-1].startswith(("bet_", "raise_")):
            actions: List[str] = ["fold", "call"]
            raise_count = sum(action.startswith("raise_") for action in history)
            if raise_count < self.raise_cap:
                actions.extend(self._sizing_actions("raise", state))
            return tuple(actions)
        raise ValueError(f"No legal actions for history: {history}")

    def _sizing_actions(self, kind: str, state: ActionState) -> Tuple[str, ...]:
        player = state.actor
        opponent = 1 - player
        previous = state.contributions[player]
        opponent_contribution = state.contributions[opponent]
        sizes = self.bet_sizes if kind == "bet" else self.raise_sizes
        actions: List[str] = []
        targets = set()
        for fraction in sizes:
            increment = self.pot * fraction
            target = increment if kind == "bet" else opponent_contribution + increment
            target = min(target, self.effective_stack)
            target = round(target, 6)
            if target <= opponent_contribution or target <= previous or target in targets:
                continue
            targets.add(target)
            actions.append(f"{kind}_{int(round(fraction * 100))}")
        return tuple(actions)

    def _apply(self, state: ActionState, action: str) -> ActionState:
        player = state.actor
        opponent = 1 - player
        contributions = list(state.contributions)
        if action == "call":
            contributions[player] = contributions[opponent]
        elif action.startswith("bet_"):
            contributions[player] = min(self.pot * self._fraction(action), self.effective_stack)
        elif action.startswith("raise_"):
            contributions[player] = min(
                contributions[opponent] + self.pot * self._fraction(action),
                self.effective_stack,
            )
        return ActionState(state.history + (action,), tuple(contributions), state.first_player)

    def _terminal_utility(
        self,
        state: ActionState,
        hero: Sequence[CardValue],
        villain: Sequence[CardValue],
        final_board: Sequence[CardValue],
    ) -> float | None:
        if not self._is_terminal(state.history):
            return None
        if state.history[-1] == "fold":
            folding_player = (state.first_player + len(state.history) - 1) % 2
            if folding_player == 0:
                return -(self.pot / 2.0 + state.contributions[0])
            return self.pot / 2.0 + state.contributions[1]

        outcome = winner(hero, villain, final_board)
        if outcome == 0:
            return 0.0
        total_pot = self.pot + sum(state.contributions)
        rake = min(total_pot * self.rake_pct, self.rake_cap) if self.rake_cap > 0 else total_pot * self.rake_pct
        if outcome > 0:
            return self.pot / 2.0 + state.contributions[1] - rake / 2.0
        return -(self.pot / 2.0 + state.contributions[0] - rake / 2.0)

    @staticmethod
    def _is_terminal(history: History) -> bool:
        if history == ("check", "check"):
            return True
        return bool(history) and history[-1] in ("fold", "call")

    @staticmethod
    def _valid_sizes(sizes: Sequence[float], name: str) -> Tuple[float, ...]:
        normalized = tuple(sorted({round(size, 2) for size in sizes if size > 0}))
        if not normalized:
            raise ValueError(f"At least one positive {name} size is required.")
        return normalized

    @staticmethod
    def _fraction(action: str) -> float:
        return int(action.split("_", maxsplit=1)[1]) / 100.0

    @staticmethod
    def _info_key(player: int, private_hand: Sequence[CardValue], board: Sequence[CardValue], state: ActionState) -> str:
        hand_key = ",".join(sorted(f"{rank}:{suit}" for rank, suit in private_hand))
        board_key = ",".join(f"{rank}:{suit}" for rank, suit in board)
        history_key = ",".join(state.history) or "root"
        return f"P{player}|{hand_key}|{board_key}|{history_key}"

    @staticmethod
    def _prepare_range(
        supplied: Sequence[WeightedCombo] | None,
        unavailable: set[CardValue],
    ) -> List[Tuple[Tuple[CardValue, CardValue], float]] | None:
        if not supplied:
            return None
        prepared: List[Tuple[Tuple[CardValue, CardValue], float]] = []
        for combo in supplied:
            cards = parse_cards(combo.cards)
            if len(cards) != 2 or cards[0] == cards[1]:
                raise ValueError("Each range combo must contain two distinct cards.")
            if set(cards) & unavailable:
                continue
            prepared.append(((cards[0], cards[1]), combo.weight))
        if not prepared:
            raise ValueError("Villain range has no legal combos after known cards are removed.")
        return prepared

    @staticmethod
    def _sample_villain(
        deck: Sequence[CardValue],
        range_combos: List[Tuple[Tuple[CardValue, CardValue], float]] | None,
        rng: random.Random,
    ) -> List[CardValue]:
        if range_combos is None:
            return rng.sample(list(deck), 2)
        combos, weights = zip(*range_combos)
        return list(rng.choices(combos, weights=weights, k=1)[0])
