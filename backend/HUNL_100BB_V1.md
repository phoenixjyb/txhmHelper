# HUNL 100bb v1 Solver Specification

## Status

This document defines the target for the first production-quality solver
pipeline. It is a heads-up no-limit Hold'em abstraction, not an exact solution
of unrestricted NLHE and not a multiway solver.

The deployed `/v1/solve` endpoint remains a bounded one-street CFR+ service
while this engine is built and validated offline.

## Fixed game

| Item | v1 definition |
| --- | --- |
| Variant | Heads-up no-limit Hold'em cash game |
| Effective stack | 100 big blinds at hand start |
| Blinds | 0.5bb small blind, 1bb big blind |
| Rake | 5% of the final pot, capped at 3bb; configurable for validation |
| Positions | Small blind/button (IP postflop), big blind (OOP postflop) |
| Streets | Preflop, flop, turn, river |
| Postflop bet sizes | 33%, 50%, 75%, 100%, 150% pot, all-in |
| Raise cap | Three raises per street plus all-in |
| Preflop tree | Limp, 2.5x open, 3x open, 3-bet, 4-bet, all-in; refined after postflop gate |

## Public state

Each solver node is keyed by the following public data:

```text
street
canonical public board
pot and remaining stacks (bucketed in bb)
street contributions
player to act / in-position player
aggressor and raise count
public action history
abstraction version
```

Private information is the acting player's exact hole-card combo or its
hand/board bucket. Unknown cards are sampled as chance events and never appear
in an information-set key.

## Solver method

1. Build the public tree from the fixed action abstraction.
2. Apply CFR+ with external chance sampling and weighted private ranges.
3. Store cumulative regrets and average strategies by abstract information set.
4. Solve offline until the configured iteration/time budget is met.
5. Persist a versioned strategy artifact and serve it through the API.

The online API only queues a job, reports its version and progress, and returns
an existing artifact or a bounded refinement. A phone must not wait for a
full-game solve.

## Abstraction phases

### Gate A — turn/river

- Exact card combos, one board canonicalizer, no neural model.
- Turn action tree followed by a real river action tree.
- Benchmark CPU terminal evaluation, then a CUDA batch evaluator.
- Acceptance: deterministic state transitions, legal action tests, toy-game
  convergence tests, and reproducible solve artifacts.

### Gate B — flop through river

- Flop tree transitions into the validated turn/river tree.
- Board texture and hand-strength buckets control memory growth.
- Compare exact-combo and bucketed results on a held-out spot set.

### Gate C — preflop

- Add the fixed preflop action tree and preflop range artifacts.
- Join to the postflop abstraction only after Gate B is stable.

## GPU plan

The RTX 4090 is useful for batched terminal payoff evaluation, board/runout
sampling, and later policy/value distillation. It does not by itself make a
correct solver.

The GPU gate is passed only when all of the following are true:

- CUDA is visible inside the service venv.
- A real poker terminal-evaluation batch runs on CUDA, not a synthetic tensor.
- Benchmark output records CPU/GPU throughput, batch size, device name, and
  deterministic seed.
- A correctness test compares GPU values with the CPU evaluator.

Until then `/health` must report `gpu_accelerated: false`.

## Non-goals for v1

- Six-max or multiway GTO.
- Dynamic arbitrary sizing entered by the phone.
- Claims of exact full-NLHE exploitability.
- Replacing the Android multiway equity view with a fake multiway GTO result.
