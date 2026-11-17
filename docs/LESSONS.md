# Lessons from trades we watched lose

These are not rules that traders *declare*. They are mistakes we *saw*: in live streams, replayed
tick by tick, and in journals. Any recipe you test should say, before the numbers, which of these
it avoids and how (the `rules_to_recipe.md` prompt asks for it).

### A1. Stop inside the noise
Several live short trades were stopped out by one or two ticks, with stops a little beyond the last
candle and not beyond the structure. In every one of them the direction was right: the target was
reached later the same day. Before the target, the price moved against the trade by about 1.5 to 4.5
times the stop distance.
**Lesson:** put the stop beyond the normal adverse noise, not just beyond the last candle.

### A2. Entering before the nearby liquidity is taken
Just above those stops sat an untouched high (sometimes several equal highs). The price went to take
it, triggered the stops, then fell. The only winning setup of that session was entered right *after*
a candle swept those highs and closed back below; its worst adverse move was tiny.
**Lesson:** if there is an untaken high/low (or equal highs/lows) just beyond the stop, either wait
until it is taken or place the stop beyond it.

### A3. Stop just beyond the most traded price
Two stops sat a few cents beyond the session's point of control, a price the market kept revisiting.
**Lesson:** do not park a stop right beyond a level where price keeps returning.

### A4. Against a strong move
On a violent opening move, every trade in its direction won, including those the trader skipped;
the counter-trend trades lost, even after a sweep of the lows.
**Lesson:** no entries against a strong impulse in progress.

### A5. A big aggressive order alone is not a signal
The strongest burst of aggressive buying of the week preceded a losing short "against" it, while the
winning trade had a modest one. A "dirty market" reading did not separate winners from losers either.
**Lesson:** do not use the size of an order-flow burst as the main filter.

### A6. A hard cap on stop size throws away the right trades
A trader refused setups whose stop exceeded a fixed cap, even at 1:6 reward. The move he had drawn
happened almost exactly, only slower. He took no trade that day.
**Lesson:** a rigid stop cap loses the right moves; a wider stop with a smaller position keeps the
risk the same.

### A7. Fixed 1:1 targets with tight stops
With stops of a few ticks or points and a 1R target, the cost is a large share of the risk, and the
journal's result per trade kept falling. At 1:1 you need more than 55% winners once costs are 0.10 R.
**Lesson:** tight stops and 1:1 targets let costs and noise eat the edge.

### A8. Early breakeven, and examples chosen afterwards
A manual exit at breakeven left a 2R target on the table; a breakeven stop missed a target by a few
points; the setups a trader skipped "for safety" would have won.
**Lesson:** move to breakeven only after the price has taken a liquidity level in your favour, not
at a fixed distance. And never judge a method by the examples its author chose to show.

### A9. A too-strict higher-timeframe filter
A "macro structure" that a trader read on one timeframe corresponded to a stricter two-timeframe
filter in our recipes, which then never entered on the days the trader was right.
**Lesson:** an over-strict context filter removes the good trades along with the bad ones.

---

## The stop rule we used afterwards

- The stop goes **beyond the farthest** of: the structural extreme of the setup; the nearest untaken
  liquidity (swing high/low, equal highs/lows) within a distance fixed in advance; the session's
  most traded price if it is closer than half an ATR.
- It is at least the typical adverse noise (a multiple of ATR fixed **before**, from charts and from
  the adverse excursion of winning trades, never from profits).
- No cap on the stop as an entry filter: reduce the position so that the risk stays the same.
- Always report the cost in R and the maximum adverse excursion of winners against the stop.

**What happened when we did it:** the wider stop raised the share of targets hit (from about 18% to
about 30% in one recipe) and lowered the cost in R. But it did exactly the same on **fake levels**
and at **other hours**. The improvement came from the geometry of the trade, not from the trader's
"place" or timing. That is the most useful finding of all: an attractive change in the results is
not evidence that the guru's idea works.
