# Red flags before you pay a trading guru (or copy their trades)

Each flag comes from something we actually saw while testing social-media trading methods. One flag
alone proves nothing. Several together mean: do not pay, do not copy, ask for verifiable evidence.

| # | What you see | Why it matters | How to check |
|---|---|---|---|
| 1 | **"90%+ win rate"** | With realistic stops and costs, very high win rates usually come from counting something else, or from tiny targets and huge losses. | Ask: per trade or per day? What is the average win vs the average loss in R? |
| 2 | **Win rate counted by days** | A high share of positive days can hide many losing trades; breakeven days get sold as "no losing day". | `metrics.win_rate_by_days`: compare trade win rate with day win rate. |
| 3 | **Only winners in the lessons** | Examples are chosen after the outcome is known. Lesson examples were almost all winners, while the trader's own journal showed far more non-winning trades (losses and breakeven). | Count taken trades in *full* sessions, never in clips. |
| 4 | **Setups drawn after the fact** | A position box drawn once the next candle is visible is not a trade. | Check the timestamps: was the box on screen before the move? |
| 5 | **Percentages summed across accounts** | A monthly percentage was the sum of several accounts' percentages, far less on the total capital. | Ask for the result on the total capital, in money. |
| 6 | **Falling result per trade** | One honest journal showed a shrinking per-trade result over a few weeks. | `metrics.expectancy_by_period` on their own journal. |
| 7 | **Promised frequency vs observed** | Several trades a week promised; none taken in a full day of live streaming. | Watch full live sessions, count what is actually executed. |
| 8 | **Teaches one thing, does another live** | Different instrument, hours, stop size or entry trigger live than in the lessons. | Compare the extracted rules with the live trades (status `taken`). |
| 9 | **"The real filters are in the course"** | The decisive part is exactly the part you cannot check. | Ask for a track record that already includes those filters. |
| 10 | **Trades opened before the stream, exits never shown** | The result is told, not seen. | Count only trades with entry *and* exit on screen. |
| 11 | **"The vision was right" after a loss** | A stopped trade counted as a success because the price later went the right way. | A stopped trade is a loss. (It may also mean stops inside the noise: see LESSONS A1.) |
| 12 | **Vague rules** ("it depends", "with experience you'll see it") | A rule that cannot be written cannot be tested, and cannot be taught either. | Try writing the recipe; list what is missing. |
| 13 | **Backtests done by scrolling the chart** | Zones redrawn after the move, losing night trades removed "because I don't trade at night". | Ask for rules written before, and results on a later period. |
| 14 | **Contradictions between videos** | Different stop rules, timeframes, "never do X" followed by doing X. | The rules prompt lists contradictions with sources. |
| 15 | **Results only on evaluation or demo accounts, or screenshots** | Easy to cherry-pick; not the same as money at risk over time. | Ask for broker statements over 6-12 months, including losing months. |
| 16 | **Very tight stops with 1:1 targets** | Costs can eat 10-50% of the risk; you need >55% winners just to break even with a 0.10 R cost. | `nulltests.breakeven_win_rate(1, cost_r)`. |
| 17 | **Selling signals, VIP groups, courses or broker links as the main business** | Income from followers does not depend on trading results. | Not proof of anything, but raise the bar for evidence. |

## Quick checklist before you invest or subscribe

- [ ] Is there a track record verified by a third party (broker statements, an audited account), over at least 6-12 months, including losses?
- [ ] Is the win rate per trade, with average win and average loss in R?
- [ ] Did you see full sessions with real entries and exits, not only clips?
- [ ] Do the rules taught match the trades done live?
- [ ] Are the rules precise enough to write down? Is anything "only in the course"?
- [ ] Do the results include spread, commissions and slippage?
- [ ] Is the result stable over time, or shrinking?
- [ ] Have the rules been tested by someone else against random entries and fake levels, on a later period?
- [ ] Would you still pay if the guru earned nothing from your subscription, your deposit or your losses?

If you tick fewer than all of them, keep your money.
