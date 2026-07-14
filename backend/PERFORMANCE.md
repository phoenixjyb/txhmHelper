# Solver Performance Operations

The API keeps one solver worker by default. This is intentional: CUDA currently
accelerates terminal showdown evaluation, while CFR traversal also consumes CPU.
Increase concurrency only after observing the queue and latency metrics on the
deployment GPU.

## Runtime controls

Set these on the server service when needed:

```ini
Environment=TXHM_SOLVER_WORKERS=1
Environment=TXHM_RESULT_CACHE_LIMIT=512
Environment=TXHM_JOB_TTL_SECONDS=3600
Environment=TXHM_RESULT_CACHE_PATH=/home/converge/data/yanbo/txhmHelper/backend/server/runtime/solve_result_cache.json
```

- `TXHM_SOLVER_WORKERS`: concurrent CFR jobs. Keep at `1` until the 4090 and
  CPU measurements show safe headroom.
- `TXHM_RESULT_CACHE_LIMIT`: maximum completed, exact-request results retained
  in the persistent LRU cache.
- `TXHM_JOB_TTL_SECONDS`: terminal job metadata retention period. Cached solver
  results use their own LRU limit.

## Runtime checks

Use direct LAN requests so a local proxy cannot distort results:

```bash
curl --noproxy '*' http://192.168.100.100:10102/health
curl --noproxy '*' http://192.168.100.100:10102/v1/metrics
```

`/v1/metrics` reports queue depth, active jobs, completed-result cache entries,
in-flight and completed-result cache hits, terminal failures/cancellations, and
average completed-solve duration.

`DELETE /v1/solve/{job_id}` immediately cancels queued work. For an already
running solve it suppresses the obsolete result; it does not interrupt a CFR
iteration already executing.

## Promotion gate for more concurrency

Collect at least 20 cold solves and 20 repeated solves for each target street.
Record p50/p95 end-to-end time, `queue_depth`, result-cache hit rate, GPU memory
use, and CPU use. Only test `TXHM_SOLVER_WORKERS=2` when the one-worker queue is
the dominant latency source and GPU memory remains comfortably below capacity.

The larger speed step is serving validated offline CFR+ artifacts for common
abstracted spots. Do not promote a Gate B artifact to runtime serving until it
passes the held-out stability and root-policy acceptance criteria.
