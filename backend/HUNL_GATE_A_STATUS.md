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

The second checkpoint moved too much to call converged. This artifact must not
be served through the phone API as GTO advice.

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

Promotion needs at least five successive checkpoint deltas below 0.01 on this
spot, a separate-seed rerun, and a held-out spot comparison. Root stability is
only a necessary operational gate, not a formal exploitability proof.
