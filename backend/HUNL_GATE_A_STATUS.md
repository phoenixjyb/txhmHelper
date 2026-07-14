# HUNL Gate A — Turn/River Status

## Current capability

`hunl.turn_river_cfr.TurnRiverCfrPlus` is an offline, two-player, zero-sum
external-sampling CFR+ trainer. It begins from a fixed turn spot, samples a
legal opponent hand and river card for each traversal, and transitions from a
turn action tree to river action trees before terminal settlement.

It persists cumulative CFR+ regrets and average strategies in a versioned JSON
artifact. The artifact is intentionally ignored by Git: it is a trained model
output, not source truth.

The Gate A action abstraction is deliberately bounded to 33%, 75%, 100%,
all-in, and one raise per street. This is narrower than the final HUNL v1 tree.

## Verified server pilot

Environment: RTX 4090 server, CUDA terminal evaluator, fixed spot
`As,Kd` on `Jh,Td,2c,7h`, 10bb pot, 90bb remaining stacks.

| Checkpoint | Total iterations | Information sets | Artifact size | Root-policy max delta |
| --- | ---: | ---: | ---: | ---: |
| 1 | 250 | 30,156 | 11 MB | n/a |
| 2 | 500 | 55,258 | 19 MB | 0.126115 |
| 3 | 1,500 | 146,825 | 49 MB | 0.016653 |
| 4 | 3,250 | 290,273 | 97 MB | 0.004535 |
| 5 | 5,250 | 446,615 | 149 MB | 0.002044 |

At 2,250, 2,500, 2,750, 3,000, and 3,250 total iterations, the primary spot
recorded root-policy deltas below 0.01. This passes the local root-stability
check for that one spot only. It is still not an API-serving artifact and is not
a formal exploitability result.

A fresh independent primary artifact reached 5,250 iterations with the same
bounded tree. Its root-policy maximum difference from the first artifact is
0.008071. That completes the practical repeatability gate for Gate A; it does
not replace formal exploitability measurement.

## Held-out spot

The held-out spot (`Qh,9h` on `Js,7d,3c,2s`, same pot and stack) exercised a
five-card canonical-board path that exposed and then fixed a four-suit mapping
bug. Its CUDA run is valid, but remains unstable at 1,000 iterations:

| Total iterations | Information sets | Artifact size | Root-policy max delta |
| ---: | ---: | ---: | ---: |
| 250 | 28,126 | 10 MB | n/a |
| 500 | 51,868 | 18 MB | 0.103703 |
| 750 | 75,134 | 26 MB | 0.058308 |
| 1,000 | 97,555 | 33 MB | 0.028363 |

The held-out artifact reached 3,250 iterations and recorded sub-1% deltas from
1,750 onward. Together with the independent-primary comparison, Gate A is
accepted as the validated input to Gate B development. It remains an offline
research artifact and must not be returned to the phone as full GTO.

## Next acceptance gate

Run fixed-size checkpoints with independent seeds and record root-policy delta:

```bash
cd backend/server
.venv/bin/python train_turn_river.py \
  --hero As,Kd --board Jh,Td,2c,7h --pot-bb 10 --stack-bb 90 \
  --iterations 5000 --checkpoint-interval 500 \
  --artifact ../artifacts/turn-river-gate-a-pilot.json --resume \
  --cuda-terminal-evaluator --seed 20260716
```

Gate B must now add a flop abstraction with board/hand bucketing before any
large-scale flop training. Root stability is only a necessary operational gate,
not a formal exploitability proof.
