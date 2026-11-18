# CLUTCH IQ 2.0 — WPL and First-Innings Par Upgrade Report

## Implemented changes

1. WPL now calculates expected absolute change in batting-side win probability over a past-only joint distribution of next-delivery runs, wicket and legal-ball status.
2. Each possible outcome is simulated by updating score, wickets, legal balls remaining and chase requirements; current delivery outcome is not used.
3. WPL is normalized by the 95th percentile calculated from a training-fold calibration sample; that scale is carried into the future scored fold.
4. First-innings par is predicted at the current state from format, balls elapsed, wickets lost, innings length and phase, using earlier matches only.
5. A temporal calibration slice within the training fold estimates a score offset; the final par model is refit on all training matches.

## Formulae

`WPL(S) = Σ_o P(o | S) × |WP(S_o) − WP(S)|`

Possible outcome `o` = (team runs 0–6 or 7+, wicket 0/1, legal-ball indicator 0/1). Conditional frequencies are grouped by format, innings, phase, wickets-lost band and required-run-rate band, then smoothed toward the training-fold global distribution.

`ParDeficit_t = PredictedParScore_t − ActualScoreBeforeDelivery_t`

## Chronological validation diagnostics

### Win-probability model

| Season | Scored states | Brier | Log loss | ROC-AUC | ECE |
|---:|---:|---:|---:|---:|---:|
| 2022 | 31,311 | 0.1728 | 0.5691 | 0.8207 | 0.0265 |
| 2023 | 32,686 | 0.1895 | 0.5597 | 0.7887 | 0.0464 |
| 2024 | 44,381 | 0.1853 | 0.5414 | 0.7930 | 0.0191 |
| 2025 | 46,240 | 0.1714 | 0.5034 | 0.8231 | 0.0291 |
| 2026 | 32,631 | 0.1869 | 0.5439 | 0.7914 | 0.0403 |

### First-innings par model

| Season | Scored states | Par MAE (runs) | Bias: predicted − actual | Calibration offset |
|---:|---:|---:|---:|---:|
| 2022 | 16,584 | 11.14 | 1.72 | 4.76 |
| 2023 | 17,309 | 11.62 | -3.47 | 2.07 |
| 2024 | 23,456 | 13.51 | -0.40 | 3.96 |
| 2025 | 25,412 | 13.80 | -2.82 | 0.70 |
| 2026 | 17,468 | 15.41 | -9.94 | -1.52 |

### WPL scale diagnostics

| Season | Raw WPL mean | Training q95 scale | Scored raw q95 | Scaled WPL mean |
|---:|---:|---:|---:|---:|
| 2022 | 0.0153 | 0.0456 | — | 0.2955 |
| 2023 | 0.0153 | 0.0340 | — | 0.3922 |
| 2024 | 0.0150 | 0.0310 | — | 0.4350 |
| 2025 | 0.0145 | 0.0350 | — | 0.3837 |
| 2026 | 0.0139 | 0.0323 | — | 0.3923 |

## Interpretation and limitations

- The WPL definition is now an expected outcome-leverage calculation rather than a state-severity proxy. It still depends on the quality/calibration of the WP model and the conditional outcome distribution.
- WP metrics are chronological out-of-sample diagnostics. ECE is a decile-based expected calibration error; it is not a complete reliability analysis.
- Par MAE is the average absolute error in predicted score at the pre-delivery state. The reported bias shows systematic under/overprediction and should be reviewed by format, phase and wickets-lost group. In particular, the later-season par bias is not zero.
- Keep 2026 untouched for final model and pressure-weight selection. If weights or model settings are tuned against 2026 results, it is no longer a final holdout.
- The model predicts match-state pressure, not a player’s actual psychological state.
- Re-run ranking phases after any model or feature changes; do not mix old leaderboard files with new pressure outputs.
