# HUNL Gate B — Bounded Convergence Protocol

This protocol evaluates the current bucketed, fixed-spot, heads-up flop-to-river
CFR+ abstraction. Passing it means the particular bounded model is stable enough
for further research review. It does **not** demonstrate full-game GTO,
exploitability bounds, multiway validity, rake realism, or unrestricted bet sizing.

## Immutable run contract

Every candidate run records:

- Git commit and artifact version.
- Full game/action configuration and bucket flags.
- Case manifest version, pot, stacks, position, checkpoint cadence, iteration
  count, independent seeds, and terminal evaluator.
- The serialized `random.Random` state at every checkpoint, so resume samples
  new chance deals rather than replaying the original seed prefix.
- GPU/device details, artifact size, elapsed time, node count, and every root
  policy checkpoint delta.

Changing an action size, rake model, bucket definition, evaluator, or public
state key starts a new comparison series. Results must not be pooled across
contracts.

## Gates and acceptance criteria

### 1. Correctness gate

- CPU and CUDA terminal tests pass.
- Exact and bucketed runs use the same sampled deals for each case/seed pair.
- Checkpoint/resume preserves the root strategy within `1e-12` per action.
- Resume restores the persisted RNG state; artifacts without it cannot be
  resumed safely.
- All artifacts load only with their matching configuration.

### 2. Within-seed policy stability gate

For both the exact reference and bucketed candidate, train in fixed checkpoints
until the last four checkpoint deltas are all `<= 1%` at the root. A one-off
low delta is insufficient. Do not interpret a held-out exact-versus-bucketed
difference before this gate: otherwise it mixes sampling/training noise with
abstraction error.

Use `server/train_gate_b_paired.py` for this gate. It keeps separate exact and
bucketed artifacts on matched RNG streams, records both deltas plus their
current root-policy distance at every checkpoint, and can stop only after both
models satisfy the four-checkpoint condition.

### 3. Held-out abstraction gate

Use `server/validate_gate_b_abstraction.py` with the versioned held-out
manifest. The cases must be outside the pilot spot set.

Use `server/run_gate_b_heldout_batch.py` to establish the paired stability
precondition sequentially for every case/seed pair. It is resumable, skips
already-stable jobs, applies the artifact/time caps, and writes a batch summary
after each completed job.

Use `server/compare_gate_b_stable_artifacts.py` to compare only the pairs that
have passed this stability precondition. It reads saved roots without training,
reports incomplete jobs as pending, and produces the per-stratum error summary
used for the acceptance threshold.

- At least four board/private-hand strata and three independent seeds, using
  the same stable iteration/checkpoint contract for exact and bucketed runs.
- Report maximum root-action error and total variation between exact and
  bucketed policies for every case/seed pair.
- Research-review target: median maximum action error `<= 5%`; hard review
  stop: any held-out maximum action error `> 15%`.

These are practical abstraction thresholds, not exploitability guarantees.

### 4. Cross-seed stability gate

At least three independently trained artifacts for the same exact spot/config
must have maximum root-action difference `<= 2.5%` pairwise. Larger drift means
continue training, improve sampling, or revise the abstraction; do not publish
recommendations.

Use `server/compare_gate_b_cross_seed_artifacts.py` on the same stable
artifact directory. It reports every exact and bucketed model pair separately;
the exact reference must satisfy the gate too, otherwise an exact-vs-bucketed
difference still contains unresolved training noise.

For a cross-seed convergence pilot, pass `--full-budget` to
`run_gate_b_heldout_batch.py`. The default runner stops once it has established
the within-seed prerequisite; full-budget mode deliberately continues to the
requested iteration cap so an early low checkpoint delta cannot masquerade as
repeatability.

Use `--continue-stable --full-budget` to resume an already-stable matched pair
for another bounded iteration budget. This retains its serialized RNG state and
checkpoint history, producing a cumulative run rather than restarting or
mixing independent samples.

### 5. Resource and stop rules

- Stop before an artifact exceeds 2 GB or a checkpoint exceeds 30 minutes.
- Stop and inspect if node growth or checkpoint time more than doubles twice in
  succession.
- Stop and revise the bucket design if the held-out hard review threshold is
  exceeded after two larger pilot attempts.

## Promotion boundary

Only a run passing all gates can be labelled **stable for the bounded Gate B
model** in research material. It still remains offline until a separate API
contract, artifact-selection policy, monitoring, and user-facing limitation
labels are reviewed. The Android app must not call it "full GTO".

## Revision history

The first held-out series used a private-hand bucket that combined all
unpaired high-card hands with the same made-hand/draw/relation labels. Its
completed comparison breached the 15% hard-review limit on the dry-broadway
stratum (22.59% maximum root-action error). The next series uses artifact
version `hunl_flop_turn_river_external_sampling_cfr_plus_v2_rank_profile` and
adds the unordered two-card rank pattern (for example `AK` or `Q9`) to the
private bucket. It is a new contract: the old v1 artifacts must not be resumed
or compared with it.
