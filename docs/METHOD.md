# The method in 6 steps

The goal is not to prove that someone is lying. The goal is to answer one narrow question with
data: **do the rules this person teaches, and the trades this person shows, beat chance after
costs?** Everything below is designed so that you cannot fool yourself, in either direction.

```
1 collect  ->  2 transcribe + frames  ->  3 extract claims, rules, trades
      ->  4 verify trades on real prices  ->  5 recipe + preregistration  ->  6 tests against chance
```

---

## 1. Collect only public, legally obtainable material

- Collect what the trader publishes: lessons, shorts, reels, recorded and live streams, posts.
- Use the tools in `fuffaguru.capture` (built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and
  ffmpeg) **with your own account**: they read pages with the cookies of your browser or a
  `cookies.txt` you export yourself into `secrets/` (ignored by git). Nothing secret goes in the
  repository. Details, limits and what is experimental: [CAPTURE.md](CAPTURE.md).
- **You are responsible** for respecting each platform's terms of service and the law of your
  country (copyright, privacy). Use the material only for your personal analysis and **never
  republish it**: share numbers and conclusions, not videos, frames or transcripts.
- Write down, for each item, the *real* date of the session. The upload date is often the day after.
- Keep what is useful, delete the rest: by default media are deleted once transcribed, and frames
  once the analysis is written (see `retention` in the settings).

## 2. Transcribe and extract frames

- `python -m fuffaguru transcribe video.mp4 --language en` uses
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and keeps a timestamp on every line.
- `python -m fuffaguru frames video.mp4 --every 2` saves a frame every 2 seconds;
  `sheet` makes contact sheets (grids) to find the interesting minutes fast.
- Read instruments, timeframes, prices and position boxes **on the frames**, never only in the text:
  automatic transcripts mangle jargon and numbers.
- Check the chart's time zone (the platform's clock, the broker's server time, local time).

## 3. Extract claims, rules and trades

Use the prompt templates in [`fuffaguru/prompts/`](../fuffaguru/prompts):

- `extract_trades.md`: every trade in the material, with a **status**:
  - `taken`: actually placed (order panel, position line, journal);
  - `skipped`: looked at and passed on, with the reason;
  - `drawn`: only drawn on the chart;
  - `told`: only told after the fact.
  Only `taken` trades are evidence of results. `told` trades are chosen afterwards: never count them.
- `extract_rules.md`: the method layer by layer (context, place, wait, trigger, entry, stop, target,
  management, invalidation, filters), each rule with its source and a tag: *said*, *seen*,
  *inferred*, *ours*.
- Record every **performance claim** and how it is counted (per trade? per day? summed over several
  accounts?), and every **contradiction** between lessons and live trading.

The CSV schema is in [`examples/trades_template.csv`](../examples/trades_template.csv) and in
`fuffaguru/trades.py` (`TRADE_COLUMNS`).

## 4. Verify the trades on real prices

```
python -m fuffaguru verify trades.csv bars.csv --cost 0.30 --max-minutes 240
```

- Bring your own bars: 1-minute bars or finer (`time,open,high,low,close`, time = bar open, UTC).
- First check that your data matches the trader's screen: compare two or three candles they show.
  Futures, spot and CFDs of the same asset differ by a few ticks; contract rolls move prices.
- For each trade the tool reports: whether the entry price was really traded in that minute, the
  outcome (target, stop, breakeven, timeout), the result in R, the cost in R, the worst adverse
  move, and **"right direction, wrong stop"**: stopped out, but the target was reached later.
- Inside one bar we do not know if the high came before the low: every ambiguity counts against the
  trade. That is deliberate.

## 5. Translate the rules into a recipe and PREREGISTER it

A recipe is the method written so that a computer can apply it without asking anything.

- Use only information available **before** the entry (a swing is known only once the bars on its
  right have closed; a higher-timeframe candle only once it has closed).
- Every number the trader does not give (swing size, zone height, tolerance) is fixed **once**, from
  charts or conventions, **before** any result. Write why.
- Write the **closing rules**: the conditions that will make you declare the idea dead (minimum
  number of trades, minimum edge over random direction, same sign in a later period...).
- Freeze it: `python -m fuffaguru freeze recipe.json` writes the recipe with its **sha256
  fingerprint and the UTC time**. `check-freeze` tells you if anyone edited it afterwards.
- After the numbers: **no tweaks**. A new variant is a new recipe, with a new fingerprint, and it
  counts as one more trial. Log every trial (`fuffaguru.prereg.log_trial`).

## 6. Put it to the test

Run all of these, and report all of them, whatever they say:

| Test | Question it answers |
|---|---|
| **Real costs** (spread + commission + slippage, in R) | Does the edge survive the price of trading? With tight stops, costs can eat 10-50% of the risk. Break-even win rate at 1:1 with a 0.10 R cost: 55%. |
| **Random direction at the same instants** | Same entry times, same stop and target distances, long or short by coin flip. Does the trader's *direction* call add anything? |
| **Fake levels / zones** | The same recipe on levels shifted at random by 0.5-3 ATR. Does the trader's *place* matter? |
| **Confirmation period** | The frozen recipe on later data it was never tuned on. |
| **Related instrument** | Same recipe on a cousin (spot vs futures of the same asset, a related metal; one equity index vs another). A real mechanism should not flip sign. |
| **Without the key filter** | The same recipe minus its "secret ingredient". If nothing changes, the ingredient is decoration. |
| **Time window alone** | If the trader trades fixed hours: random direction in the same window. Is it the hour, not the method? |
| **Always long / always short** | In a market that went up all year, any "buy the dip" recipe looks good. |

The `report` module turns all of this into one page, the **Reality Check**, with one of three
verdicts: `INCONCLUSIVE`, `NO EVIDENCE OF EDGE`, `PASSED THESE CHECKS (NOT A PROOF OF EDGE)`.

See a complete run on synthetic data in [`examples/synthetic_guru`](../examples/synthetic_guru).

---

## Typical statistical mistakes (made by sellers and by investigators)

- **Data snooping.** Try 50 variants, keep the best: it will look great by luck alone. Count every
  variant you tried and adjust the p-values (the report uses a Sidak correction). In our synthetic
  example the best of 48 variants even beats random direction in sample, then gives about zero on
  new data.
- **Choosing after the fact.** Examples picked once the outcome is known; zones redrawn after the
  move; "backtests" done by scrolling the chart; losing night trades removed "because I don't trade
  at night". None of this is evidence.
- **Win rate by days instead of trades.** A "90%+ winning" claim can count positive days, with
  many losing trades inside them. Breakeven days get sold as "no losing day". Always ask: per trade?
- **Breakeven inflating the win rate.** Moving the stop to entry early turns many losers into zeros
  and makes the hit rate look high, without improving the result.
- **Small samples.** A few dozen trades with a high win rate still have a very wide confidence interval. A good month proves very little; neither does a bad one.
- **Regime.** A rising market makes every long look smart. Compare with "always long" at the same
  instants, and test a different period.
- **Look-ahead.** Using a swing, a zone or a daily candle before it was known.
- **Costs ignored.** Results quoted before spread and commissions, on stops of a few ticks.
- **Survivorship.** You only see the sellers who are still around, and only the trades they chose
  to show.
- **Our own completion.** When the decisive part of a method is kept "for the paid course", a
  mechanical test measures *our* completion of the rules, not the seller's method. Say so.
