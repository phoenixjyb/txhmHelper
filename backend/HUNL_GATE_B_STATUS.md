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

Checkpoint artifacts persist the chance-sampling RNG state. Resumed training
continues with new deals rather than replaying its original seed prefix; legacy
artifacts without that state are rejected for resume.

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

### Initial held-out diagnostic — 2026-07-14

The first server report completed four held-out strata across three seeds with
25 fresh iterations per exact/bucketed comparison. It reported 20.73% mean,
20.48% median, and 36.98% maximum root-action difference; mean root total
variation was 22.90%. This is well outside the protocol target and hard-review
threshold.

At this intentionally short depth the result combines training/sampling noise
with abstraction error, so it is a **failed pre-convergence diagnostic**, not a
measurement of the final bucket quality. It confirms the harness can reject an
unsafe candidate. The protocol now requires exact and bucketed runs to satisfy
within-seed stability before the held-out numbers are used for promotion.

## Paired within-seed stability pilot — 2026-07-14

The paired checkpoint runner preserves matched chance samples across exact and
bucketed artifacts, writes their root deltas at every checkpoint, and enforces
artifact configuration matching on resume.

For the original fixed spot (`As,Kd` on `Jh,Td,2c`, 10 bb pot, 90 bb effective,
Hero OOP, seed `20260719`), the RTX 4090 run stopped at 800 iterations after
passing the within-seed gate. The last four exact/bucketed root deltas were:

| Total iterations | Exact delta | Bucketed delta | Cross-model root gap |
| ---: | ---: | ---: | ---: |
| 725 | 0.86% | 0.27% | 14.68% |
| 750 | 0.74% | 0.20% | 15.44% |
| 775 | 0.97% | 0.19% | 16.34% |
| 800 | 0.81% | 0.18% | 17.09% |

The final exact artifact contains 266,347 nodes / 90 MB; bucketed contains
45,042 nodes / 19 MB. This validates checkpointing and confirms a substantial
memory reduction, but the 17.09% matched root-policy gap means the bucketed
model is **not accepted**. This result passes only the within-seed stability
prerequisite, not the held-out abstraction or cross-seed gates.

## Next research gate

Run paired stability jobs for every held-out case/seed, then compare each
stable exact artifact against its stable bucketed counterpart. Do not reuse the
25-iteration held-out diagnostic as an abstraction-quality measurement.

The sequential batch runner starts or resumes all four held-out cases across
three seeds and writes `batch-summary.json` after every job:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python run_gate_b_heldout_batch.py \
  --seeds 20260716,20260717,20260718 \
  --output-dir ../artifacts/gate-b-heldout-stability-20260714 \
  --iterations-per-job 800 --checkpoint-interval 25 \
  --job-timeout-seconds 1800 --max-artifact-mb 2048 \
  --cuda-terminal-evaluator
```

The one-spot paired command is:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python train_gate_b_paired.py \
  --hero As,Kd --board Jh,Td,2c --pot-bb 10 --stack-bb 90 \
  --iterations 800 --checkpoint-interval 25 --stop-on-stable \
  --exact-artifact ../artifacts/gate-b-exact-paired-20260714.json \
  --bucketed-artifact ../artifacts/gate-b-bucketed-paired-20260714.json \
  --report ../artifacts/gate-b-paired-20260714.json \
  --cuda-terminal-evaluator --seed 20260719
```

Only after stable held-out comparison can we decide whether bucket features
need refinement or larger bucketed pilots are justified.

Gate B remains offline research infrastructure. The deployed `/v1/solve`
endpoint remains the bounded one-street CFR+ service; it does not read these
artifacts or provide full-flop GTO advice.
