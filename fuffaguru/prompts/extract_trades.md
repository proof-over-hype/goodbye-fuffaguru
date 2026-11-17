# Prompt: extract trades from a timestamped transcript (and frame notes)

Use this with any capable LLM. Paste the transcript (with `[hh:mm:ss]` stamps) and, if you have
them, short notes on what the frames show (instrument, timeframe, price axis, position box).

---

You are a careful analyst. From the material below, extract EVERY trade the speaker shows or talks
about, including trades they did NOT take. Do not judge the trader. Do not guess.

Statuses:
- `taken`: an order placed, seen on screen (position line, order panel, P/L) or clearly stated as
  being placed now;
- `skipped`: a setup they looked at and decided not to take; write their reason in `notes`;
- `drawn`: a position or arrow only drawn on the chart, never executed;
- `told`: a trade only told after the fact ("this morning I took...", screenshots of past wins).

For each trade, fill one CSV row with these columns, in this order:

`trade_id,source,source_time,status,instrument,side,entry_time,entry_price,stop_price,target_price,claimed_result_r,confidence,notes`

Rules:
1. `source_time` is the stamp in the transcript where the trade appears. Mandatory.
2. Prices only if SEEN on a frame or SAID with numbers. Never compute or invent a price. Empty if unknown.
3. `entry_time`: the market time of the entry if it can be read from the chart axis or from the
   clock, in ISO-8601 with the time zone you are sure of; otherwise empty and explain in `notes`.
   Warning: the upload date of a video is often NOT the day of the session.
4. `confidence`: `high` (number read on screen), `medium` (read from the axis or said once),
   `low` (inferred).
5. In `notes`, separate clearly: SAID: ... / SEEN: ... / INFERRED: ...
6. Also list, after the CSV, every PERFORMANCE CLAIM (win rate, returns, trades per week, "never
   lose", "X% this month"), with its stamp, and HOW it is counted if said (by trade, by day, by
   account, summed across accounts...).
7. List CONTRADICTIONS between what is taught and what is done (different instrument, hours,
   stop size, entry type), with stamps.
8. Output only: the CSV block, then "CLAIMS:", then "CONTRADICTIONS:". No commentary on the person.

MATERIAL:
<<<paste transcript and frame notes here>>>
