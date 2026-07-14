# HUNL Gate B — Bucketed Flop to River Status

## Implemented source gate

`FlopTurnRiverCfrPlus` now starts from a three-card flop and traverses real
flop, turn, and river action trees. It samples a legal opponent combo plus turn
and river chance cards, keeps future cards out of earlier information-set keys,
and uses a distinct artifact version from Gate A.

The RTX 4090 smoke run used the CUDA terminal evaluator and produced nodes on
all three streets. This verifies public-state transitions and terminal payoff
routing, not strategic convergence.

The versioned board-texture and private-hand buckets are active for Gate B. A
20-sample server comparison reduced observed information sets from 1,496 to
1,008 and wall time from 1.12s to 0.62s. The shared offline trainer accepts
`--stage flop`, supports checkpoint/resume, and creates a distinct Gate B
artifact.

## First CUDA pilot — 2026-07-14

Two independent CUDA-terminal pilots ran on the RTX 4090 for the fixed HUNL
spot `As,Kd` on `Jh,Td,2c`, 10 bb pot, 90 bb effective stacks, Hero OOP. Both
used the bucketed Gate B action model and 125 external-sampling CFR+ iterations.

| Pilot | Seed | Nodes | Artifact size | Last 25-iteration root delta |
| --- | ---: | ---: | ---: | ---: |
| A | 20260714 | 16,793 | 6.8 MB | 2.34% |
| B | 20260715 | 19,419 | 7.8 MB | 3.77% |

The maximum difference between their average root action probabilities was
13.41%. This is useful evidence that checkpointing, bucketing, and CUDA payoff
routing work at a small scale. It is also clear evidence that 125 iterations
is **not converged**. These artifacts are research diagnostics only and must
not be exposed as GTO recommendations.

## Held-out comparison harness and run protocol

`server/validate_gate_b_abstraction.py` now runs fresh exact and bucketed Gate B
trainers against the same chance samples for every case/seed pair. It writes a
versioned JSON report containing per-action root-policy error, root total
variation, node counts, and summaries stratified by board texture and
private-hand bucket. The fixed manifest is intentionally outside the original
pilot spot.

The bounded acceptance, stop, and promotion rules live in
[`HUNL_GATE_B_CONVERGENCE_PROTOCOL.md`](HUNL_GATE_B_CONVERGENCE_PROTOCOL.md).
They are practical stability checks for this abstraction, not a claim of formal
exploitability or full-game GTO.

First server validation command:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python validate_gate_b_abstraction.py \
  --iterations 25 --seeds 20260716,20260717,20260718 \
  --cuda-terminal-evaluator \
  --output ../artifacts/gate-b-heldout-20260714.json
```

## Next research gate

1. Run the held-out report with at least three seeds and inspect the error
   strata against the protocol thresholds.
2. If the abstraction gate is acceptable, run larger checkpointed pilots using
   the fixed run contract and evaluate within- and cross-seed stability.
3. If it is not acceptable, refine bucket features or the action model before
   increasing training depth.

Gate B remains offline research infrastructure. The deployed `/v1/solve`
endpoint remains the bounded one-street CFR+ service; it does not read these
artifacts or provide full-flop GTO advice.
