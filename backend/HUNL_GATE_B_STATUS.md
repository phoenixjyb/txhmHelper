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

## Completed v1 held-out stability series — 2026-07-14

The RTX 4090 completed all four held-out strata across the three independent
seeds at the 800-iteration, 25-iteration-checkpoint contract. Every exact and
bucketed pair passed the within-seed stability prerequisite, so the saved
artifact roots are valid for the held-out abstraction comparison.

| Held-out stratum | Pairs | Mean max action error | Worst max action error |
| --- | ---: | ---: | ---: |
| Paired trips | 3 | 2.82% | 3.46% |
| Wet connected combo draw | 3 | 4.87% | 5.95% |
| Monotone high-card | 3 | 8.24% | 9.17% |
| Dry broadway high-card | 3 | 15.83% | 22.59% |

Across all 12 pairs, the median maximum root-action error was 6.62%, the mean
was 7.94%, and the worst case was 22.59%. The median misses the 5% research
target and the dry-broadway case breaches the 15% hard-review stop. Therefore
the v1 bucketed artifact is **rejected** and remains offline research data.

## Completed v2 rank-profile series — 2026-07-15

The v2 rank-profile bucket reduced the 12-pair median maximum root-action
error from 6.62% to 4.42%, and the mean from 7.94% to 5.58%. However, its worst
held-out pair was still 17.76% (dry broadway), exceeding the 15% hard-review
limit, so v2 is **not accepted** either.

The new cross-seed report explains why it would be premature to revise the
bucket again: the exact reference itself was not repeatable at the early-stop
depth. Its worst pairwise root-action differences were 11.76% on dry broadway,
7.17% on monotone high-card, and 5.79% on wet connected; only paired trips
passed the 2.5% cross-seed requirement. The observed exact-vs-bucketed gaps
therefore still include material training noise.

## Next research gate — v2 full-budget convergence pilot

Keep the v2 abstraction fixed and run the three dry-broadway seeds to a deeper
iteration budget without the default early-stability stop. This isolates the
cross-seed question before another abstraction revision:

The v2 bucket adds the unordered hole-card rank pattern to each private
information set while preserving suit/draw and board-texture abstraction. It
has a new artifact version, so the v1 files cannot be resumed or compared with
v2. Run the same held-out matrix into a new output directory:

The sequential batch runner starts or resumes all four held-out cases across
three seeds and writes `batch-summary.json` after every job:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python run_gate_b_heldout_batch.py \
  --seeds 20260716,20260717,20260718 \
  --output-dir ../artifacts/gate-b-v2-rank-profile-deep-20260715 \
  --iterations-per-job 3000 --checkpoint-interval 50 \
  --job-timeout-seconds 3600 --max-artifact-mb 2048 --max-jobs 3 \
  --full-budget \
  --cuda-terminal-evaluator
```

As stable pairs arrive, compare them without retraining:

```bash
.venv/bin/python compare_gate_b_stable_artifacts.py \
  --seeds 20260716,20260717,20260718 \
  --input-dir ../artifacts/gate-b-v2-rank-profile-deep-20260715 \
  --output ../artifacts/gate-b-v2-rank-profile-deep-20260715/stable-comparison.json \
  --cuda-terminal-evaluator
```

Then run `compare_gate_b_cross_seed_artifacts.py` against the same deep
directory. Only if the exact reference clears 2.5% pairwise should a remaining
exact-vs-bucketed gap be attributed to the abstraction.

### First full-budget result

At 3,000 cumulative iterations, the three dry-broadway exact-vs-bucketed
comparisons improved to 3.28% median, 4.14% mean, and 6.88% maximum
root-action error. The bucketed policy was cross-seed repeatable (0.96%
maximum), but the exact reference was not yet: its worst pairwise difference
was 3.74%, narrowly above the 2.5% gate. Resume these three artifacts for a
second 3,000-iteration full budget rather than changing the abstraction:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python run_gate_b_heldout_batch.py \
  --seeds 20260716,20260717,20260718 \
  --output-dir ../artifacts/gate-b-v2-rank-profile-deep-20260715 \
  --iterations-per-job 3000 --checkpoint-interval 50 \
  --job-timeout-seconds 3600 --max-artifact-mb 2048 --max-jobs 3 \
  --full-budget --continue-stable \
  --cuda-terminal-evaluator
```

### Dry-broadway acceptance at 6,000 iterations

The resumed dry-broadway artifacts completed 6,000 cumulative iterations on
each of the three matched seeds. This bounded stratum now passes both gates:

| Measure | Result | Gate |
| --- | ---: | ---: |
| Exact-vs-bucketed median root-action error | 1.81% | <= 5% target |
| Exact-vs-bucketed maximum root-action error | 3.45% | <= 15% hard stop |
| Bucketed cross-seed maximum root-action drift | 0.53% | <= 2.5% |
| Exact cross-seed maximum root-action drift | 1.60% | <= 2.5% |

This accepts the **dry-broadway stratum only** for the bounded v2 model. It
does not promote v2 to API serving, because the other three held-out strata
have not yet passed the same full-budget and cross-seed checks.

## Next research gate — remaining three strata

Use the existing deep artifact directory. The runner skips the accepted
dry-broadway pairs and trains the nine missing wet-connected, paired-trips, and
monotone-high pairs from scratch at 6,000 iterations:

```bash
cd /home/converge/data/yanbo/txhmHelper/backend/server
.venv/bin/python run_gate_b_heldout_batch.py \
  --seeds 20260716,20260717,20260718 \
  --output-dir ../artifacts/gate-b-v2-rank-profile-deep-20260715 \
  --iterations-per-job 6000 --checkpoint-interval 50 \
  --job-timeout-seconds 7200 --max-artifact-mb 2048 \
  --full-budget \
  --cuda-terminal-evaluator
```

After the batch, regenerate both `stable-comparison` and `cross-seed` reports
from the full directory. Only an all-four-strata pass permits the next backend
step: a constrained artifact-selection API behind explicit bounded-solver
labels.

Only after v2 passes the held-out and cross-seed gates can we design the
artifact-selection API. It will still be a bounded postflop research solver,
not full-game or multiway GTO.

Gate B remains offline research infrastructure. The deployed `/v1/solve`
endpoint remains the bounded one-street CFR+ service; it does not read these
artifacts or provide full-flop GTO advice.
