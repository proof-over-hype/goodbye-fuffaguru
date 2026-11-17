# Reality Check - synthetic guru (example)

> **Verdict: NO EVIDENCE OF EDGE**

Why:

- the 95% bootstrap interval of the mean result includes zero or less
- does not beat the null 'fake levels (shifted)' (p = 1.000 after adjusting for 48 trials)
- the frozen recipe loses in the confirmation period (-0.007 R)

Warnings:

- claimed win rate 53% versus 35% measured on trades (the claim counts days, not trades)
- the mean result falls over time (+0.58 R in the first block, -0.22 R in the last)

## Verified trades (status 'taken')

| Measure | Value |
|---|---|
| Trades | 214 |
| Wins / losses / breakeven | 35% / 65% / 0% |
| Mean result before costs | +0.264 R |
| Mean cost | 0.044 R |
| Mean result after costs | +0.220 R |
| 95% bootstrap interval of the mean | -0.014 to +0.463 R |
| Total | +47.1 R |
| Profit factor | 1.33 |
| Max drawdown | 22.5 R |

## Claimed versus measured

| Measure | Value |
|---|---|
| Winning trades | 35% |
| Positive days | 53% of 59 days |
| Days not negative (often sold as 'no losing day') | 53% |
| Claimed win rate | 53% (counted by: days) |

Other claims recorded:

- Shows 12 winning trades out of 13 examples (picked after the fact).

## Null tests

p = probability of doing at least as well by chance (one-sided). Adjusted p accounts for 48 registered trials (Sidak).

| Test | Observed | Null mean | Null 5%-95% | p | Adjusted p |
|---|---|---|---|---|---|
| random direction, same instants | +0.220 | -0.084 | -0.235 to +0.068 | <0.001 | 0.024 |
| fake levels (shifted) | +0.220 | +0.164 | +0.004 to +0.302 | 0.248 | 1.000 |

Same instants, fixed direction: always long -0.343 R, always short +0.175 R (share of long trades: 40%).

## Right direction, wrong stop

54 of 134 stopped trades reached their target later within the horizon. Median adverse move before the target: 2.0 times the stop distance.

## Trades by status

Skipped and drawn setups show whether the trader's own filters help; 'told' trades are chosen after the fact and never count as evidence.

| Status | Count | Mean result after costs |
|---|---|---|
| taken | 214 | +0.220 R |

## Result over time

| Block | From | To | Trades | Mean R |
|---|---|---|---|---|
| 1 | 2024-01-03 | 2024-01-24 | 72 | +0.582 |
| 2 | 2024-01-24 | 2024-02-15 | 71 | +0.289 |
| 3 | 2024-02-15 | 2024-03-03 | 71 | -0.215 |

## Confirmation period (frozen recipe, new data)

| Measure | Value |
|---|---|
| Trades | 664 |
| Mean result after costs | -0.007 R |
| Random direction p | 0.088 |
| Fake levels p | 0.608 |

## Notes

- Synthetic random-walk market: no rule can have a real edge here, by construction.
- The rules tested are the best of 48 variants chosen on the development period.
- Recipe fingerprint (sha256): 1fd40f3d9f64e1b6eba848082aac58ae1139a0969d1325ce687d9caafc7a9379.

## What this does not say

- This is an educational analysis, not financial advice.
- It describes rules and trades as we could read and test them, not the intentions or honesty of anyone.
- A failed test of a translated recipe does not prove that a trader has no skill: it shows that the rules as taught, written down and tested, do not beat chance. A passed test is not a proof of skill either: it can be luck, a favourable period, or selection.
- Only results that a third party can verify (broker statements over many months, including losing periods) can support a claim of consistent profitability.
