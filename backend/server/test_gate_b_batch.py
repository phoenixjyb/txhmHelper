import json
import tempfile
import unittest
from pathlib import Path

from hunl.gate_b_batch import build_held_out_jobs, stable_report_summary, write_json_atomic
from hunl.gate_b_validation import load_held_out_cases


class GateBBatchTest(unittest.TestCase):
    def test_batch_jobs_have_unique_artifact_paths(self):
        manifest = Path(__file__).parent / "hunl" / "gate_b_heldout_cases_v1.json"
        jobs = build_held_out_jobs(load_held_out_cases(manifest)[:2], (7, 11), "/tmp/gate-b")
        self.assertEqual(4, len(jobs))
        self.assertEqual(4, len({job.exact_artifact for job in jobs}))
        self.assertTrue(jobs[0].bucketed_artifact.name.endswith("-bucketed.json"))

    def test_stable_summary_requires_stable_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            write_json_atomic(report, {"stable": False, "history": []})
            self.assertIsNone(stable_report_summary(report))
            write_json_atomic(report, {"stable": True, "history": [{"total_iterations": 800}]})
            self.assertEqual(800, stable_report_summary(report)["total_iterations"])
            self.assertEqual({"stable": True, "history": [{"total_iterations": 800}]}, json.loads(report.read_text()))


if __name__ == "__main__":
    unittest.main()
