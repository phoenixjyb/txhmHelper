# HUNL Gate B — Flop to River Status

## Implemented source gate

`FlopTurnRiverCfrPlus` now starts from a three-card flop and traverses real
flop, turn, and river action trees. It samples a legal opponent combo plus turn
and river chance cards, keeps future cards out of earlier information-set keys,
and uses a distinct artifact version from Gate A.

The RTX 4090 smoke run used the CUDA terminal evaluator and produced nodes on
all three streets. This verifies public-state transitions and terminal payoff
routing, not strategic convergence.

## Why a long flop run is not started yet

Gate A exact-combo artifacts reached roughly 150 MB per 5,250-iteration turn
spot. Starting one street earlier multiplies private-hand and board-state
coverage sharply. Training the exact-combo flop tree blindly would spend memory
without producing a credible general strategy artifact.

## Next implementation gate

Add versioned abstractions for:

1. Canonical flop/turn board texture buckets.
2. Private hand-strength/draw buckets conditional on the public board.
3. A held-out exact-combo comparison harness, so bucketed policies can be
   measured against the validated Gate A path before they are trained at scale.

Until these exist, Gate B remains an offline traversal smoke gate, and the
deployed `/v1/solve` endpoint remains the bounded one-street CFR+ service.
