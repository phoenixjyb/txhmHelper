import time
import unittest

import main


class V1ApiTest(unittest.TestCase):
    def setUp(self):
        with main.jobs_lock:
            main.jobs.clear()
            main.cache.clear()

    def test_queued_solve_completes_and_is_cached(self):
        payload = main.V1SolvePayload(
            stage="flop",
            hole=["As", "Kd"],
            board=["Jh", "Td", "2c"],
            pot=10.0,
            effective_stack=100.0,
            iterations=100,
        )

        created = main.create_v1_solve(payload)
        self.assertEqual("queued", created.status)
        cached = main.create_v1_solve(payload)
        self.assertEqual(created.job_id, cached.job_id)
        self.assertTrue(cached.cache_hit)

        completed = created
        for _ in range(100):
            completed = main.get_v1_solve(created.job_id)
            if completed.status in ("complete", "failed"):
                break
            time.sleep(0.02)

        self.assertEqual("complete", completed.status, completed.error)
        self.assertIsNotNone(completed.result)
        self.assertEqual("cpu_reference", completed.result.terminal_evaluator)
        self.assertAlmostEqual(1.0, sum(completed.result.strategy.values()), places=8)


if __name__ == "__main__":
    unittest.main()
