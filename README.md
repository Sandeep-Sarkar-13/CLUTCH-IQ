# CLUTCH IQ 2.0 — WPL and first-innings par upgrade

Self-contained project. No imports from the old baseline project are required.

## Install (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the phases in order

```powershell
python src/phase1_data_foundation.py
python src/phase2_3_models.py
python src/phase4_hybrid_pressure.py
python src/phase5_player_rankings.py
python src/phase6_validation_report.py
```

Or run everything with `python src/run_pipeline.py --phase all`.

## Upgraded methodology

### A. Win-Probability Leverage (WPL)

For each pre-delivery state S, the model estimates the expected absolute change in
batting-team win probability across possible next-delivery outcomes:

`WPL(S) = Σ_o P(o | S) × |WP(S_o) − WP(S)|`

Each possible outcome jointly represents:
- Team runs: 0, 1, 2, 3, 4, 5, 6, or 7+;
- Whether a wicket falls;
- Whether the delivery consumes a legal ball.

The outcome distribution is estimated from earlier-fold deliveries only, conditional
on match format, innings, phase, wickets-lost band and required-run-rate band. A
Dirichlet-style prior smooths sparse groups toward the earlier-fold global outcome
distribution. The realised current delivery outcome is never used to calculate its
own pressure score.

The win-probability model predicts the batting side's probability of winning from
pre-delivery match state. For each hypothetical outcome, the code updates score,
wickets, legal balls remaining and chase requirements, then predicts WP for the
simulated state. Chase terminal states (target reached, all out, or overs exhausted)
are assigned exact 1/0 outcomes where appropriate.

Raw WPL is normalized by the 95th percentile of WPL calculated on a deterministic
sample of the training fold. The same training-fold scale is applied to its future
scored fold. This keeps the WPL component on a comparable 0–1 scale without using
future-season outcomes to set the scale.

### B. First-innings par model

For each chronological fold, a HistGradientBoostingRegressor is trained on earlier
first-innings delivery states. It predicts the expected score at the current point
of the innings from:
- Format (T20/T20I);
- Legal balls already bowled;
- Wickets lost;
- Innings ball limit;
- Phase fraction.

The model target is the observed pre-delivery score (`score_before`), and the score
itself is deliberately not a predictor. It therefore estimates a historical par
curve for the current resource state.

`ParDeficit = PredictedParScore − ActualScoreBeforeDelivery`

Positive values mean the batting side is below historical par; negative values mean
it is above par. The model is retrained per chronological fold using only earlier
matches. The MAE and mean prediction bias are exported by year.

### C. Leakage controls

- Train and scored folds have disjoint match IDs.
- All WP inputs are pre-delivery state features.
- Outcome probabilities are estimated from the training fold only.
- Hypothetical post-delivery states are simulated; actual current delivery outcomes
  do not enter WPL.
- First-innings par predictions use earlier matches only.
- Early warm-up matches in 2022 have no out-of-sample prediction and are excluded
  from player ranking calculations.

## Re-run after upgrading WPL/par

Because pressure scores and player rankings depend on both upgraded components,
rerun Phase 2/3 onward:

```powershell
python src/phase2_3_models.py
python src/phase4_hybrid_pressure.py
python src/phase5_player_rankings.py
python src/phase6_validation_report.py
```

Do not rerun Phase 1 unless the raw-data processing rules or source files change.

## Outputs to inspect

- `data/processed/oos_predictions.csv.gz`: raw WPL, normalized WPL, pre-delivery WP,
  expected par score and par deficit for each scored delivery.
- `data/processed/deliveries_v2_pressure.csv.gz`: final HDPI, BPI and BoPI features.
- `outputs/model_metrics.json`: per-fold WP Brier score, log loss, ROC-AUC, ECE,
  expected-performance MAE, par MAE/bias and WPL scaling diagnostics.
- `outputs/methodology_and_validation_report.json`: formula and review checklist.
- `outputs/top10_*_relaxed/current/strict.csv`: player rankings.

## Important limitations before competition submission

1. The WP model is a logistic baseline. Review reliability diagrams and calibration
   separately for T20/T20I, innings and phase. Brier/log loss and ECE are diagnostics,
   not proof of perfect calibration.
2. The conditional outcome distribution is a smoothed empirical distribution with
   five context dimensions. Inspect sample support and outcome fit by group; test
   alternate conditioning schemes and calibration.
3. The par model is a historical state-conditioned regression curve, not a full
   cricket simulator. Inspect residuals by phase, wickets lost and format.
4. The 2026 fold should remain untouched while tuning weights or models.
5. HDPI weights and eligibility thresholds remain design choices; run ablations and
   ranking stability tests before claiming superiority over the baseline.
6. Situational responsibility features are observable match-context proxies, not
   direct measurements of player psychology.
7. Verify the source-data definitions for `Overstep`, extras and revised innings
   limits before final submission.
