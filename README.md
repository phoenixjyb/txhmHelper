# TX Hold'em Helper

Android (Jetpack Compose) app that lets you tap in hole + community cards and see live odds for each hand category. Preflop uses Monte Carlo sampling for instant response, flop/turn/river use exact enumeration.

## Structure
- `app/src/main/java/com/txhmhelper/model`: card/rank/suit models, board state, hand types.
- `app/src/main/java/com/txhmhelper/odds`: odds engine (`OddsCalculator`) with Monte Carlo preflop, exact postflop, and a simple 7-card evaluator.
- `app/src/main/java/com/txhmhelper/ui`: Compose screen + ViewModel wiring.
- `app/src/main/java/com/txhmhelper/ui/theme`: theme colors/typography.
- `app/src/test/java/com/txhmhelper/odds`: unit tests for the evaluator and compute guardrails.

## Running
Open in Android Studio (Giraffe+), sync Gradle, and run on API 26+.
- Precision toggle: Fast (~80k samples, ~250ms budget) vs High (~320k samples, ~800ms budget) for preflop.
- Odds switch to exact mode automatically after the flop.

## Testing
`./gradlew :app:test` (or `gradle :app:test` if you do not use the wrapper) runs unit tests for the evaluator and compute guardrails.

## Next improvements
- Swap in a faster precomputed 7-card evaluator for higher preflop accuracy without long sampling.
- Add outs estimation per hand and a variance/confidence display for Monte Carlo.
- Optional multi-player odds once the single-player flow is solid.
- GTO backend stub included in `backend/server` (FastAPI, Dockerfile). Replace `solver.py` with a real solver (CFR/LCFR) and deploy on a GPU box (e.g., 4090). Mobile client Retrofit interfaces live in `app/src/main/java/com/txhmhelper/gto`.
