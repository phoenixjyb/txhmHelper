"""Turn-to-river external-sampling CFR+ gate for the HUNL abstraction.

This module deliberately starts at a turn decision with a sampled opponent hand
and river card. Turn information sets never contain that future river card;
river information sets do. Both players' actions are traversed on every sampled
deal, so it is a genuine two-player zero-sum CFR+ traversal across two streets,
not a turn-only solver with a sampled showdown.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from solver_cfr import CardValue, parse_cards, winner

from .abstraction import public_state_key
from .buckets import private_hand_bucket
from .game import Action, GameConfig, PublicState, Street, advance_street, apply_action, initial_postflop_state, legal_actions

ARTIFACT_VERSION = "hunl_turn_river_external_sampling_cfr_plus_v1"
FLOP_TURN_RIVER_ARTIFACT_VERSION = "hunl_flop_turn_river_external_sampling_cfr_plus_v1"


@dataclass
class CfrPlusNode:
    actions: Tuple[str, ...]
    regrets: Dict[str, float] = field(init=False)
    strategy_sum: Dict[str, float] = field(init=False)

    def __post_init__(self) -> None:
        self.regrets = {action: 0.0 for action in self.actions}
        self.strategy_sum = {action: 0.0 for action in self.actions}

    def strategy(self, reach_probability: float) -> Dict[str, float]:
        positive = {action: max(0.0, self.regrets[action]) for action in self.actions}
        total = sum(positive.values())
        current = (
            {action: positive[action] / total for action in self.actions}
            if total > 0
            else {action: 1.0 / len(self.actions) for action in self.actions}
        )
        for action, probability in current.items():
            self.strategy_sum[action] += reach_probability * probability
        return current

    def average_strategy(self) -> Dict[str, float]:
        total = sum(self.strategy_sum.values())
        if total == 0:
            return {action: 1.0 / len(self.actions) for action in self.actions}
        return {action: value / total for action, value in self.strategy_sum.items()}

    def to_dict(self) -> Dict[str, object]:
        return {
            "actions": list(self.actions),
            "regrets": self.regrets,
            "strategy_sum": self.strategy_sum,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CfrPlusNode":
        node = cls(tuple(payload["actions"]))
        node.regrets = {str(key): float(value) for key, value in dict(payload["regrets"]).items()}
        node.strategy_sum = {str(key): float(value) for key, value in dict(payload["strategy_sum"]).items()}
        if set(node.actions) != set(node.regrets) or set(node.actions) != set(node.strategy_sum):
            raise ValueError("Regret artifact node has inconsistent actions.")
        return node


@dataclass(frozen=True)
class TurnRiverTrainingConfig:
    """Bounded Gate A action tree; later artifacts may widen it after validation."""

    game: GameConfig = field(
        default_factory=lambda: GameConfig(
            postflop_bet_sizes=(0.33, 0.75, 1.0),
            postflop_raise_sizes=(0.75, 1.5),
            max_raises_per_street=1,
        )
    )
    artifact_version: str = ARTIFACT_VERSION
    use_gpu_terminal_evaluator: bool = False
    use_board_texture_buckets: bool = False
    use_private_hand_buckets: bool = False


@dataclass(frozen=True)
class FlopTurnRiverTrainingConfig:
    """Gate B configuration; kept separate so flop artifacts cannot mix with Gate A."""

    game: GameConfig = field(
        default_factory=lambda: GameConfig(
            postflop_bet_sizes=(0.33, 0.75, 1.0),
            postflop_raise_sizes=(0.75, 1.5),
            max_raises_per_street=1,
        )
    )
    artifact_version: str = FLOP_TURN_RIVER_ARTIFACT_VERSION
    use_gpu_terminal_evaluator: bool = False
    use_board_texture_buckets: bool = True
    use_private_hand_buckets: bool = True


@dataclass(frozen=True)
class TurnRiverResult:
    strategy: Dict[str, float]
    iterations: int
    total_iterations: int
    node_count: int
    root_key: str
    artifact_version: str
    terminal_evaluator: str


class TurnRiverCfrPlus:
    """Persistent exact-combo turn/river CFR+ trainer for a fixed public spot."""

    def __init__(self, config: TurnRiverTrainingConfig | None = None) -> None:
        self.config = config or TurnRiverTrainingConfig()
        self.nodes: Dict[str, CfrPlusNode] = {}
        self.total_iterations = 0

    def train(
        self,
        hero_hand: Sequence[str],
        turn_board: Sequence[str],
        pot_bb: float,
        stacks_bb: Tuple[float, float],
        hero_position: str,
        iterations: int,
        rng: random.Random | None = None,
    ) -> TurnRiverResult:
        return self._train_from_street(
            hero_hand, turn_board, pot_bb, stacks_bb, hero_position, iterations, Street.TURN, rng
        )

    def train_flop(
        self,
        hero_hand: Sequence[str],
        flop_board: Sequence[str],
        pot_bb: float,
        stacks_bb: Tuple[float, float],
        hero_position: str,
        iterations: int,
        rng: random.Random | None = None,
    ) -> TurnRiverResult:
        """Gate B entry point: traverse flop, turn, and river decisions."""
        return self._train_from_street(
            hero_hand, flop_board, pot_bb, stacks_bb, hero_position, iterations, Street.FLOP, rng
        )

    def _train_from_street(
        self,
        hero_hand: Sequence[str],
        board_cards: Sequence[str],
        pot_bb: float,
        stacks_bb: Tuple[float, float],
        hero_position: str,
        iterations: int,
        starting_street: Street,
        rng: random.Random | None,
    ) -> TurnRiverResult:
        hero = parse_cards(hero_hand)
        board = parse_cards(board_cards)
        expected_board_cards = {Street.FLOP: 3, Street.TURN: 4}
        if starting_street not in expected_board_cards or len(hero) != 2 or len(board) != expected_board_cards[starting_street]:
            raise ValueError("Training requires two hole cards and a board matching the requested starting street.")
        if set(hero) & set(board):
            raise ValueError("Hero cards and board cards must not overlap.")
        if iterations < 1:
            raise ValueError("iterations must be positive.")
        if hero_position not in ("oop", "ip"):
            raise ValueError("hero_position must be 'oop' or 'ip'.")

        first_to_act = 0 if hero_position == "oop" else 1
        root = initial_postflop_state(starting_street, board_cards, pot_bb, stacks_bb, first_to_act)
        if root.to_act != 0:
            raise ValueError("Gate A currently returns a root strategy only when Hero is OOP on the turn.")

        generator = rng or random.Random()
        remaining = [
            (rank, suit)
            for rank in range(13)
            for suit in range(4)
            if (rank, suit) not in set(hero) | set(board)
        ]
        future_cards = 5 - len(board)
        sampled_deals = []
        for _ in range(iterations):
            villain = generator.sample(remaining, 2)
            runout = tuple(generator.sample([card for card in remaining if card not in villain], future_cards))
            sampled_deals.append((villain, runout))
        outcomes = self._showdown_outcomes(hero, board, sampled_deals)

        for (villain, runout), outcome in zip(sampled_deals, outcomes):
            self._cfr(
                state=root,
                hero=hero,
                villain=villain,
                runout=runout,
                showdown_outcome=outcome,
                hero_reach=1.0,
                villain_reach=1.0,
            )
        self.total_iterations += iterations

        root_key = self._info_key(root, hero, legal_actions(root, self.config.game))
        return TurnRiverResult(
            strategy=self.nodes[root_key].average_strategy(),
            iterations=iterations,
            total_iterations=self.total_iterations,
            node_count=len(self.nodes),
            root_key=root_key,
            artifact_version=self.config.artifact_version,
            terminal_evaluator="cuda_batched" if self.config.use_gpu_terminal_evaluator else "cpu_reference",
        )

    def save_artifact(self, path: str | Path, metadata: Dict[str, object] | None = None) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "artifact_version": self.config.artifact_version,
            "training_config": {
                "game": asdict(self.config.game),
                "use_gpu_terminal_evaluator": self.config.use_gpu_terminal_evaluator,
                "use_board_texture_buckets": self.config.use_board_texture_buckets,
                "use_private_hand_buckets": self.config.use_private_hand_buckets,
            },
            "metadata": metadata or {},
            "total_iterations": self.total_iterations,
            "nodes": {key: node.to_dict() for key, node in self.nodes.items()},
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(destination)

    def root_strategy(
        self,
        hero_hand: Sequence[str],
        turn_board: Sequence[str],
        pot_bb: float,
        stacks_bb: Tuple[float, float],
        hero_position: str = "oop",
    ) -> Dict[str, float]:
        """Read the current average strategy for an already-trained OOP root."""
        if hero_position != "oop":
            raise ValueError("Gate A root strategy is currently defined only for an OOP hero.")
        hero = parse_cards(hero_hand)
        if len(hero) != 2 or len(turn_board) != 4:
            raise ValueError("Turn/river root strategy requires two hole cards and four board cards.")
        state = initial_postflop_state(Street.TURN, turn_board, pot_bb, stacks_bb, first_to_act=0)
        key = self._info_key(state, hero, legal_actions(state, self.config.game))
        if key not in self.nodes:
            raise ValueError("Artifact does not contain the requested root information set.")
        return self.nodes[key].average_strategy()

    @classmethod
    def load_artifact(cls, path: str | Path, config: TurnRiverTrainingConfig | None = None) -> "TurnRiverCfrPlus":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        expected = (config or TurnRiverTrainingConfig()).artifact_version
        if payload.get("artifact_version") != expected:
            raise ValueError("Regret artifact version does not match the requested training config.")
        trainer = cls(config)
        trainer.nodes = {key: CfrPlusNode.from_dict(value) for key, value in payload["nodes"].items()}
        trainer.total_iterations = int(payload.get("total_iterations", 0))
        return trainer

    def _cfr(
        self,
        state: PublicState,
        hero: Sequence[CardValue],
        villain: Sequence[CardValue],
        runout: Sequence[CardValue],
        showdown_outcome: int,
        hero_reach: float,
        villain_reach: float,
    ) -> float:
        if state.terminal:
            return self._terminal_utility(state, showdown_outcome)
        if state.street_complete:
            if state.street == Street.FLOP:
                return self._cfr(
                    advance_street(state, _card_label(runout[0])), hero, villain, runout, showdown_outcome, hero_reach, villain_reach
                )
            if state.street == Street.TURN:
                return self._cfr(
                    advance_street(state, _card_label(runout[-1])), hero, villain, runout, showdown_outcome, hero_reach, villain_reach
                )
            return self._cfr(
                advance_street(state, None), hero, villain, runout, showdown_outcome, hero_reach, villain_reach
            )

        player = state.to_act
        private = hero if player == 0 else villain
        actions = legal_actions(state, self.config.game)
        action_map = {action.label: action for action in actions}
        key = self._info_key(state, private, actions)
        node = self.nodes.setdefault(key, CfrPlusNode(tuple(action_map)))
        if node.actions != tuple(action_map):
            raise ValueError("Action abstraction collision: information set has incompatible legal actions.")
        strategy = node.strategy(hero_reach if player == 0 else villain_reach)

        action_values: Dict[str, float] = {}
        node_value = 0.0
        for label, action in action_map.items():
            child = apply_action(state, action, self.config.game)
            if player == 0:
                value = self._cfr(child, hero, villain, runout, showdown_outcome, hero_reach * strategy[label], villain_reach)
            else:
                value = self._cfr(child, hero, villain, runout, showdown_outcome, hero_reach, villain_reach * strategy[label])
            action_values[label] = value
            node_value += strategy[label] * value

        counterfactual_reach = villain_reach if player == 0 else hero_reach
        for label, value in action_values.items():
            regret = value - node_value if player == 0 else node_value - value
            node.regrets[label] = max(0.0, node.regrets[label] + counterfactual_reach * regret)
        return node_value

    def _showdown_outcomes(
        self,
        hero: Sequence[CardValue],
        board: Sequence[CardValue],
        sampled_deals: Sequence[Tuple[Sequence[CardValue], Sequence[CardValue]]],
    ) -> List[int]:
        if not self.config.use_gpu_terminal_evaluator:
            return [winner(hero, villain, list(board) + list(runout)) for villain, runout in sampled_deals]

        from .gpu import probe_gpu
        from .torch_evaluator import showdown_equity

        status = probe_gpu()
        if not status.available:
            raise RuntimeError(f"CUDA terminal evaluator requested but unavailable: {status.reason}")
        import torch

        hero_cards = torch.tensor(
            [_cards_tensor(hero, list(board) + list(runout)) for _, runout in sampled_deals], device="cuda", dtype=torch.long
        )
        villain_cards = torch.tensor(
            [_cards_tensor(villain, list(board) + list(runout)) for villain, runout in sampled_deals], device="cuda", dtype=torch.long
        )
        equities = showdown_equity(hero_cards, villain_cards).cpu().tolist()
        return [1 if equity == 1.0 else -1 if equity == 0.0 else 0 for equity in equities]

    def _terminal_utility(self, state: PublicState, showdown_outcome: int) -> float:
        if state.folded_player is not None:
            if state.folded_player == 0:
                return -(state.pot_bb / 2.0 + state.street_committed_bb[0])
            return state.pot_bb / 2.0 + state.street_committed_bb[1]
        if not state.showdown or showdown_outcome == 0:
            return 0.0
        total_pot = state.pot_bb + sum(state.street_committed_bb)
        rake = min(total_pot * self.config.game.rake_pct, self.config.game.rake_cap_bb)
        if showdown_outcome > 0:
            return state.pot_bb / 2.0 + state.street_committed_bb[1] - rake / 2.0
        return -(state.pot_bb / 2.0 + state.street_committed_bb[0] - rake / 2.0)

    def _info_key(self, state: PublicState, private_cards: Iterable[CardValue], actions: Sequence[Action]) -> str:
        private_labels = tuple(_card_label(card) for card in private_cards)
        private_key = (
            private_hand_bucket(private_labels, state.board)
            if self.config.use_private_hand_buckets
            else ",".join(sorted(private_labels))
        )
        action_key = ",".join(action.label for action in actions)
        return (
            f"P{state.to_act}|{private_key}|"
            f"{public_state_key(state, self.config.artifact_version, self.config.use_board_texture_buckets)}|"
            f"actions={action_key}"
        )


def _cards_tensor(hole_cards: Sequence[CardValue], board: Sequence[CardValue]) -> List[List[int]]:
    return [[rank + 2, suit] for rank, suit in list(hole_cards) + list(board)]


def _card_label(card: CardValue) -> str:
    ranks = "23456789TJQKA"
    suits = "cdhs"
    return f"{ranks[card[0]]}{suits[card[1]]}"


class FlopTurnRiverCfrPlus(TurnRiverCfrPlus):
    """Semantic Gate B trainer using the same tested multi-street CFR+ core."""

    def __init__(self, config: FlopTurnRiverTrainingConfig | None = None) -> None:
        super().__init__(config or FlopTurnRiverTrainingConfig())

    @classmethod
    def load_artifact(
        cls,
        path: str | Path,
        config: FlopTurnRiverTrainingConfig | None = None,
    ) -> "FlopTurnRiverCfrPlus":
        return super().load_artifact(path, config or FlopTurnRiverTrainingConfig())
