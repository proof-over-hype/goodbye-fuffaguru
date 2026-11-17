# Prompt: turn the extracted rules into a recipe ready to preregister

Paste the layer table produced with `extract_rules.md`. The output is a JSON (or YAML) recipe that
can be frozen with `python -m fuffaguru freeze recipe.json` BEFORE any result is computed.

---

Write a recipe with these keys:

- `name`, `source` (a neutral label, never a person's name), `hypothesis` (one sentence that can be false);
- `rules`: one entry per layer, mechanical and unambiguous, using ONLY information available before
  the entry (swings confirmed only after their right-hand bars; higher-timeframe candles only once closed);
- `thresholds`: every number the trader did not give, with the reason for the value. Choose them
  from charts or common conventions, ONCE, never from results;
- `data`: instrument(s), bar size, development period, confirmation period (later, untouched), a related
  instrument for a second check;
- `costs`: spread + commission + slippage in price units, and the median cost in R expected from the
  stop size;
- `controls`: at least random direction at the same instants, fake levels/zones, the same recipe without
  its key filter, and - if the trader trades fixed hours - the same window with random direction;
- `closing_rules`: 4-8 sentences that would make you declare the idea dead, written NOW. Include a
  minimum number of trades, a minimum edge over random direction (e.g. +0.10 R), and "same sign in the
  confirmation period";
- `variants`: at most two cells, declared now. Anything added later is a new recipe.

Also write, for each lesson in docs/LESSONS.md (A1-A9), one line: "avoided: yes/no, how".

RULES TABLE:
<<<paste here>>>
