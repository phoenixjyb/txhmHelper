import random
import unittest

from hunl.torch_evaluator import evaluate_seven, showdown_equity
from hunl.gpu import terminal_evaluator_benchmark
from solver_cfr import best_rank_seven

try:
    import torch
except ImportError:
    torch = None


@unittest.skipUnless(torch is not None and torch.cuda.is_available(), "CUDA PyTorch is not installed")
class TorchEvaluatorTest(unittest.TestCase):
    def test_straight_flush_beats_quads_on_cuda(self):
        hero = torch.tensor([[[14, 0], [13, 0], [12, 0], [11, 0], [10, 0], [2, 1], [3, 2]]], device="cuda")
        villain = torch.tensor([[[14, 1], [14, 2], [14, 3], [14, 0], [2, 0], [3, 1], [4, 2]]], device="cuda")

        hero_score = evaluate_seven(hero)
        villain_score = evaluate_seven(villain)
        equity = showdown_equity(hero, villain)

        self.assertGreater(hero_score.item(), villain_score.item())
        self.assertEqual(1.0, equity.item())

    def test_cuda_scores_match_reference_order_for_random_legal_hands(self):
        generator = random.Random(20260714)
        deck = [(rank, suit) for rank in range(13) for suit in range(4)]
        hands = [generator.sample(deck, 7) for _ in range(48)]
        cards = torch.tensor(
            [[[rank + 2, suit] for rank, suit in hand] for hand in hands],
            device="cuda",
        )
        gpu_scores = evaluate_seven(cards).cpu().tolist()
        reference_scores = [best_rank_seven(hand) for hand in hands]

        for left in range(len(hands)):
            for right in range(left + 1, len(hands)):
                expected = (reference_scores[left] > reference_scores[right]) - (reference_scores[left] < reference_scores[right])
                actual = (gpu_scores[left] > gpu_scores[right]) - (gpu_scores[left] < gpu_scores[right])
                self.assertEqual(expected, actual, msg=f"rank ordering diverged for hands {left} and {right}")

    def test_cuda_terminal_evaluator_benchmark(self):
        result = terminal_evaluator_benchmark(batch_size=512)

        self.assertEqual("batched_seven_card_terminal_evaluator", result["benchmark"])
        self.assertGreater(result["elapsed_ms"], 0)
        self.assertGreater(result["hands_per_second"], 0)


if __name__ == "__main__":
    unittest.main()
