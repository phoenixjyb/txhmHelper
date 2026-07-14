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
- All artifacts load only with their matching configuration.

### 2. Held-out abstraction gate

Use `server/validate_gate_b_abstraction.py` with the versioned held-out
manifest. The cases must be outside the pilot spot set.

- At least four board/private-hand strata and three independent seeds.
- Report maximum root-action error and total variation between exact and
  bucketed policies for every case/seed pair.
- Research-review target: median maximum action error `<= 5%`; hard review
  stop: any held-out maximum action error `> 15%`.

These are practical abstraction thresholds, not exploitability guarantees.

### 3. Within-seed policy stability gate

For each seed, train in fixed checkpoints until the last four checkpoint deltas
are all `<= 1%` at the root. A one-off low delta is insufficient.

### 4. Cross-seed stability gate

At least three independently trained artifacts for the same exact spot/config
must have maximum root-action difference `<= 2.5%` pairwise. Larger drift means
continue training, improve sampling, or revise the abstraction; do not publish
recommendations.

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
