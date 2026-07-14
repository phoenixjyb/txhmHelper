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

## Next implementation gate

Before any long production-style run:

1. Add a held-out exact-combo comparison harness against the validated Gate A
   turn/river path, stratified by flop texture and hand/draw bucket.
2. Define a convergence protocol: independent seeds, fixed checkpoint cadence,
   policy-delta thresholds, artifact-size/runtime limits, and stop rules.
3. Run larger bucketed pilots only after that harness reports their abstraction
   error, then decide whether to expand the action model or train more deeply.

Gate B remains offline research infrastructure. The deployed `/v1/solve`
endpoint remains the bounded one-street CFR+ service; it does not read these
artifacts or provide full-flop GTO advice.
