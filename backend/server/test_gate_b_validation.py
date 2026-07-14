import tempfile
import unittest
from pathlib import Path

from hunl.gate_b_validation import load_held_out_cases, run_held_out_comparison, write_report
from hunl.game import GameConfig


class GateBValidationTest(unittest.TestCase):
    def test_held_out_report_is_stratified_and_serializable(self):
        manifest = Path(__file__).parent / "hunl" / "gate_b_heldout_cases_v1.json"
        cases = load_held_out_cases(manifest)
        game = GameConfig(
            rake_pct=0.0,
            postflop_bet_sizes=(0.5,),
            postflop_raise_sizes=(1.0,),
            max_raises_per_street=1,
        )
        report = run_held_out_comparison(cases[:2], iterations=2, seeds=(7, 11), game=game)

        self.assertEqual(2, report["case_count"])
        self.assertEqual(4, report["run_count"])
        self.assertEqual(2, len(report["strata"]))
        self.assertGreaterEqual(report["summary"]["max_root_action_error"], 0.0)
        self.assertGreaterEqual(report["summary"]["median_max_root_action_error"], 0.0)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_report(report, output)
            self.assertIn("report_version", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
