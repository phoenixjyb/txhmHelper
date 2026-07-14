import time
import unittest

import main


class V1ApiTest(unittest.TestCase):
    def setUp(self):
        with main.jobs_lock:
            main.jobs.clear()
            main.cache.clear()
            main.result_cache.clear()
            main.metrics = main.RuntimeMetrics()
        main.RESULT_CACHE_PATH.unlink(missing_ok=True)

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

        # Simulate a process restart after a finished solve: the result cache,
        # rather than the in-flight job map, should answer immediately.
        with main.jobs_lock:
            main.cache.clear()
        reused = main.create_v1_solve(payload)
        self.assertTrue(reused.cache_hit)
        self.assertEqual("complete", reused.status)
        self.assertIsNotNone(reused.result)

        metrics = main.get_metrics()
        self.assertEqual(1, metrics["submitted"])
        self.assertEqual(1, metrics["result_cache_hits"])

    def test_table_solve_maps_exact_action_and_returns_mapping(self):
        payload = main.TableSolvePayload(
            stage="flop",
            hole=["As", "Kd"],
            board=["Jh", "Td", "2c"],
            pot_before_street=10.0,
            effective_stack=100.0,
            hero_position="ip",
            actions=[main.TableActionPayload(player="villain", type="bet", amount_to=6.0)],
            iterations=100,
        )

        created = main.create_table_solve(payload)
        completed = created
        for _ in range(100):
            completed = main.get_v1_solve(created.job_id)
            if completed.status in ("complete", "failed"):
                break
            time.sleep(0.02)

        self.assertEqual("complete", completed.status, completed.error)
        self.assertEqual(["bet_60"], completed.result.action_history)

    def test_cancelling_a_queued_job_removes_it_from_the_inflight_cache(self):
        job_id = "queued-job"
        cache_key = "cancel-key"
        with main.jobs_lock:
            main.jobs[job_id] = main.SolveJob(status="queued", cache_key=cache_key)
            main.cache[cache_key] = job_id

        cancelled = main.cancel_v1_solve(job_id)

        self.assertEqual("cancelled", cancelled.status)
        self.assertNotIn(cache_key, main.cache)
        self.assertEqual(1, main.get_metrics()["cancelled"])


if __name__ == "__main__":
    unittest.main()
