import json
import random
import tempfile
import unittest
from pathlib import Path

from hunl.gate_b_artifact_compare import compare_stable_artifacts
from hunl.gate_b_batch import build_held_out_jobs, write_json_atomic
from hunl.gate_b_cross_seed_compare import compare_cross_seed_stable_artifacts
from hunl.gate_b_validation import load_held_out_cases
from hunl.turn_river_cfr import FlopTurnRiverCfrPlus, FlopTurnRiverTrainingConfig


class GateBArtifactCompareTest(unittest.TestCase):
    def test_compares_stable_pair_and_leaves_missing_jobs_pending(self):
        manifest = Path(__file__).parent / "hunl" / "gate_b_heldout_cases_v1.json"
        cases = load_held_out_cases(manifest)
        with tempfile.TemporaryDirectory() as directory:
            jobs = build_held_out_jobs(cases[:2], (7,), directory)
            job = jobs[0]
            exact = FlopTurnRiverCfrPlus(FlopTurnRiverTrainingConfig(use_board_texture_buckets=False, use_private_hand_buckets=False))
            bucketed = FlopTurnRiverCfrPlus(FlopTurnRiverTrainingConfig())
            arguments = dict(
                hero_hand=job.case.hero_hand,
                flop_board=job.case.flop_board,
                pot_bb=job.case.pot_bb,
                stacks_bb=(job.case.stack_bb, job.case.stack_bb),
                hero_position="oop",
                iterations=2,
            )
            exact.train_flop(**arguments, rng=random.Random(7))
            bucketed.train_flop(**arguments, rng=random.Random(7))
            exact.save_artifact(job.exact_artifact)
            bucketed.save_artifact(job.bucketed_artifact)
            write_json_atomic(job.report, {"stable": True, "history": [{"total_iterations": 2}]})

            report = compare_stable_artifacts(jobs, use_gpu_terminal_evaluator=False)
            cross_seed = compare_cross_seed_stable_artifacts(jobs, use_gpu_terminal_evaluator=False)

        self.assertEqual(1, report["stable_pair_count"])
        self.assertEqual([jobs[1].label], report["pending_jobs"])
        self.assertIsNotNone(report["summary"])
        self.assertEqual(2, len(cross_seed["groups"]))
        self.assertEqual([jobs[1].label], cross_seed["pending_jobs"])
        self.assertEqual(0, cross_seed["groups"][0]["pair_count"])
        json.dumps(report)
        json.dumps(cross_seed)


if __name__ == "__main__":
    unittest.main()
