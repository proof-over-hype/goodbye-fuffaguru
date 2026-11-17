# Launch kit (nothing here is published automatically)

Everything below is a draft to copy by hand **after** the repository is public. Before posting
anywhere: re-read the rules of each community (they change), post from a personal account that has
some history there, answer comments, and never add names of traders or channels, even famous ones.

## Repository description (max 350 characters)

> Goodbye FuffaGuru - Reality-check your trading guru. Follow a YouTube, TikTok or Instagram trader
> with your own account, transcribe lessons and live streams, extract the trades, verify them on real
> prices and test the rules against chance (random direction, fake levels, real costs).
> Preconfigured for Claude Code.

(≈ 330 characters)

**Social preview:** `docs/assets/social-preview.png` (1280x640). Upload it in
Settings -> General -> Social preview.

## GitHub topics (max 20)

`trading` `backtesting` `quant` `statistics` `finfluencer` `scam-detection` `financial-literacy`
`trading-education` `tiktok` `youtube` `instagram` `live-streaming` `yt-dlp` `ffmpeg`
`transcription` `whisper` `claude-code` `ai-agents` `python` `open-source`

## "Awesome" lists

Check first that each list is still maintained and read its CONTRIBUTING file (format, order,
minimum stars or age, one PR per list). Propose the line only when the README, tests and example are
in good shape.

| List | Section to target | Line to propose |
|---|---|---|
| [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | Workflows / project templates | `[Goodbye FuffaGuru](https://github.com/OWNER/goodbye-fuffaguru) - Claude Code project that follows social-media trading gurus, extracts their trades and rules from transcripts, and reality-checks them against chance with preregistered tests.` |
| [awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | Python - Backtesting / Risk analysis | `[goodbye-fuffaguru](https://github.com/OWNER/goodbye-fuffaguru) - Verify trades shown by trading educators on real prices and test their rules against random-direction and fake-level nulls, with preregistration (sha256).` |
| [awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading) | Backtesting / Education | `Goodbye FuffaGuru - Reality-check a trading method: preregistered recipe, real costs, random direction at the same instants, fake levels, confirmation period.` |
| [awesome-whisper](https://github.com/sindresorhus/awesome-whisper) | Apps / Tools | `[Goodbye FuffaGuru](https://github.com/OWNER/goodbye-fuffaguru) - Records and transcribes trading live streams in 3-minute pieces with faster-whisper, to check what is said against real prices.` |
| [awesome-ai-agents](https://github.com/e2b-dev/awesome-ai-agents) | Open-source projects | `Goodbye FuffaGuru - Claude Code agents and commands that follow a trader, extract trades from transcripts and write a statistical Reality Check.` |

Replace `OWNER` with the final GitHub account.

## Reddit

General rules for all posts: lead with the findings and the data, not with the link; put the link
once, at the end; flair as required; no names of people or channels; reply to criticism with data.
Suggested times are for the community's main audience; avoid weekends for technical subs.

### r/algotrading
- **Check first:** rules on self-promotion and on linking your own projects; whether a weekly thread
  is required; flair (e.g. "Strategy" or "Education").
- **When:** Tuesday-Thursday, 14:00-16:00 UTC.
- **Title:** I reality-checked dozens of trading strategies from YouTube/TikTok gurus with preregistered tests. Here's what the data says (open-source tool inside)
- **Text:**

  > Over a few months I turned trading content into testable rules: about 300 ideas from the videos of
  > two dozen YouTube channels and two TikTok accounts, then a handful of traders followed in live
  > sessions. Every recipe was frozen (sha256) with its kill criteria *before* any result, then run
  > with real costs against: random direction at the same instants, the same recipe on fake levels,
  > a later period, and a related instrument.
  >
  > Results, in short:
  > - 18 ideas were complete enough to test; none survived. More than a dozen recipes from the live
  >   traders: all closed by their own pre-written rules.
  > - The "zones" did not matter: in one case real zones hit the target 17.8% of the time, fake
  >   zones 15.6% (p = 0.24), trades outside any zone 22.3%.
  > - A wider stop raised the hit rate from ~18% to ~30%... identically on fake levels and at
  >   other hours. Geometry, not the guru's "place".
  > - Live, one scalper's 3 trades were all stopped out, yet the direction was right in all 3: the
  >   stops sat below untaken highs (tick data).
  > - A "92% win rate" was 12 green days out of 13; the trade-level journal said 72%, with the
  >   result per trade falling from +1.4 R to +0.2 R in six weeks.
  >
  > The tool (MIT, Python): trade verification on your own bars, preregistration, null tests,
  > a markdown "Reality Check". There's a synthetic example where the best of 48 variants makes
  > +0.22 R/trade in sample (it even beats random direction) and about zero on new data.
  > Happy to hear what null I'm missing. Link: <repo URL>

### r/ClaudeAI
- **Check first:** the "Built with Claude" / project showcase flair and its required details; rules
  on links.
- **When:** Monday-Thursday, 15:00-17:00 UTC.
- **Title:** I built a Claude Code project that follows trading gurus, extracts their trades from live streams and reality-checks them
- **Text:**

  > Open the folder with Claude Code and say "follow these traders". Slash commands do the rest:
  > `/follow-trader` (history + a live watcher that checks every 60 s and records in 3-minute pieces),
  > `/analyze-live` (trades taken and skipped, with reasons, verified on prices, then cleans up the
  > media), `/reverse-engineer` (rules -> recipe -> sha256 preregistration -> null tests) and
  > `/reality-check` (a one-page verdict). Sub-agents extract trades and play the statistical critic.
  >
  > Things that cost us live sessions and are now built in: signed stream URLs expire (the recorder
  > re-reads them and keeps one session per live), a per-profile lock that also covers the pause
  > between two ffmpeg runs, and an alert when a page says "live" but no stream can be found.
  >
  > What we learned from the data: dozens of strategies from popular trading videos, none beat chance
  > after costs. MIT licence, your own account and cookies, nothing republished. <repo URL>

### r/Forex
- **Check first:** self-promotion rules (often strict), whether educational tools are allowed,
  required flair.
- **When:** Tuesday-Thursday, 12:00-14:00 UTC (London/New York overlap).
- **Title:** Before you pay for a signals group: I checked the claims of several trading educators against real prices
- **Text:**

  > No names, just what the numbers looked like:
  > - "90-100% win rate" -> counted by days, not trades. Trade-level journal: 72%.
  > - "21% this month" -> percentages of three accounts added together (about 4.5% on the total).
  > - Lessons showed 44 real trades with 2 losses; in the trader's own journal 28% of trades were not wins.
  > - With 6-15 pip stops and 1:1 targets, spread and commission ate from 7% to over 40% of the risk, depending on the pair.
  > - Live trading differed from the lessons (other instruments, other hours, wider stops).
  >
  > I put the checklist and the tools in an open-source repo (MIT): verify the trades on your own data,
  > compare with random entries at the same minutes. Not financial advice; no accusations, just data.
  > <repo URL>

### r/Daytrading
- **Check first:** rules on promotion and links (many day-trading subs remove link posts); maybe post
  as text only and add the link in a comment if allowed.
- **When:** weekdays before the US open, 12:00-13:30 UTC, or after the close, 21:00-22:00 UTC.
- **Title:** I watched day traders' live streams tick by tick. The most common way they lost: right direction, wrong stop
- **Text:**

  > In one live session, 3 real trades, all stopped out by a tick or two. Replayed on tick data, the
  > target was reached later in every one of them. The stops sat just under untaken highs; before the
  > target the price went against them by 1.5-4.5x the stop. The only clean setup of the day (which
  > the trader skipped) came right *after* those highs were swept.
  >
  > Other things we saw: a trader promising 15-20 trades a week took zero in six hours of streaming;
  > another taught "limit order at first touch" but traded with a confirmation live, and the taught
  > entry was the worst performer.
  >
  > Lessons we wrote down (stop beyond noise and untaken liquidity, no fights against strong impulses,
  > don't trust order-flow size alone) and the open-source tools are here: <repo URL>

### r/ItaliaPersonalFinance (in Italian)
- **Da controllare prima:** regole sull'autopromozione e sui link a progetti propri; flair
  (es. «Discussione» o «Investimenti»); a volte i post sul trading sono indirizzati a thread dedicati.
- **Quando:** da lunedì a giovedì, 8:00-9:00 o 13:00-14:00 ora italiana.
- **Titolo:** Ho messo alla prova decine di strategie dei «guru» del trading di YouTube e TikTok: i numeri (strumento open source)
- **Testo:**

  > Prima di pagare un corso o un gruppo di segnali, ho provato a verificare con i dati quello che
  > insegnano: circa 300 idee prese dai video di una ventina di canali YouTube e due account TikTok,
  > più alcuni trader seguiti nelle dirette. Ogni regola è stata scritta e «congelata» prima di
  > guardare i risultati, poi confrontata con ingressi a caso negli stessi minuti, con livelli finti e
  > con i costi veri.
  >
  > In breve: nessuna ha retto. Un «92% di operazioni vincenti» era in realtà 12 giornate positive su
  > 13 (il diario per operazione diceva 72%); un «21% in un mese» era la somma delle percentuali di tre
  > conti; uno prometteva 15-20 operazioni a settimana e in sei ore di diretta ne ha fatte zero.
  >
  > Ho raccolto metodo, checklist e strumenti in un progetto open source (licenza MIT). Non è
  > consulenza finanziaria e non accusa nessuno: dice solo cosa danno le regole messe alla prova.
  > <link al repository>

### r/Python (optional)
- **Check first:** the "Showcase" flair and its mandatory sections (What My Project Does, Target
  Audience, Comparison).
- **When:** Tuesday-Wednesday, 14:00-16:00 UTC.
- **Title:** Goodbye FuffaGuru: verify trades shown by trading influencers on real prices and test them against chance
- **Text:** *What My Project Does*: captures public videos and live streams with your own account
  (yt-dlp, ffmpeg), transcribes them (faster-whisper), replays the extracted trades on OHLC bars,
  freezes recipes with sha256, runs random-direction and fake-level nulls, writes a markdown report.
  *Target Audience*: retail investors, educators, quants who review strategies. *Comparison*:
  backtesting libraries assume you already have a strategy; this starts from what a person *says*
  and *shows*, and ends with a cautious verdict. MIT, tests included. <repo URL>
