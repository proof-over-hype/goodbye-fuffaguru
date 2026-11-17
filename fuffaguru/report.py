"""The "Reality Check" report: one markdown page with a cautious verdict.

The verdict is deliberately limited to three answers:

* ``INCONCLUSIVE``: too few verifiable trades to say anything;
* ``NO EVIDENCE OF EDGE``: the rules or trades, as tested, do not beat chance
  or do not survive costs;
* ``PASSED THESE CHECKS (NOT A PROOF OF EDGE)``: nothing here contradicts an
  edge. It is never a recommendation to invest.

The report describes *tested rules and verified trades*, never people.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from .metrics import expectancy_by_period, summarize_r, win_rate_by_days
from .nulltests import (NullResult, bootstrap_mean_ci, random_direction_test, same_instant_baselines,
                        sidak_adjust)

INCONCLUSIVE = "INCONCLUSIVE"
NO_EDGE = "NO EVIDENCE OF EDGE"
PASSED = "PASSED THESE CHECKS (NOT A PROOF OF EDGE)"

CAVEATS = [
    "This is an educational analysis, not financial advice.",
    "It describes rules and trades as we could read and test them, not the intentions or honesty of anyone.",
    "A failed test of a translated recipe does not prove that a trader has no skill: it shows that "
    "the rules as taught, written down and tested, do not beat chance. A passed test is not a proof "
    "of skill either: it can be luck, a favourable period, or selection.",
    "Only results that a third party can verify (broker statements over many months, including "
    "losing periods) can support a claim of consistent profitability.",
]


def _p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


@dataclass
class Claims:
    """What the seller claims, to be compared with what is measured."""

    win_rate: Optional[float] = None  # 0-1
    win_rate_basis: str = "unknown"  # 'trades', 'days' or 'unknown'
    trades_per_week: Optional[float] = None
    other: list = field(default_factory=list)


@dataclass
class RealityCheck:
    title: str
    verdict: str
    reasons: list
    warnings: list
    summary: dict
    gross_mean: float
    cost_mean: float
    ci: tuple
    days: dict
    by_status: pd.DataFrame
    periods: pd.DataFrame
    nulls: list
    adjusted_p: list
    baselines: dict
    stop_check: dict
    confirmation: Optional[dict]
    claims: Optional[Claims]
    notes: list
    n_trials: int
    alpha: float

    # ------------------------------------------------------------ rendering
    def to_markdown(self) -> str:
        L = [f"# {self.title}", "", f"> **Verdict: {self.verdict}**", ""]
        if self.reasons:
            L += ["Why:", ""] + [f"- {r}" for r in self.reasons] + [""]
        if self.warnings:
            L += ["Warnings:", ""] + [f"- {w}" for w in self.warnings] + [""]

        s = self.summary
        L += ["## Verified trades (status 'taken')", ""]
        if s.get("n", 0) == 0:
            L += ["No verifiable taken trades.", ""]
        else:
            L += [
                "| Measure | Value |", "|---|---|",
                f"| Trades | {s['n']} |",
                f"| Wins / losses / breakeven | {s['win_rate']:.0%} / {s['loss_rate']:.0%} / {s['breakeven_rate']:.0%} |",
                f"| Mean result before costs | {self.gross_mean:+.3f} R |",
                f"| Mean cost | {self.cost_mean:.3f} R |",
                f"| Mean result after costs | {s['mean']:+.3f} R |",
                f"| 95% bootstrap interval of the mean | {self.ci[0]:+.3f} to {self.ci[1]:+.3f} R |",
                f"| Total | {s['total']:+.1f} R |",
                f"| Profit factor | {s['profit_factor']:.2f} |",
                f"| Max drawdown | {s['max_drawdown']:.1f} R |",
                "",
            ]

        L += ["## Claimed versus measured", ""]
        d = self.days
        if d.get("trades"):
            L += [
                "| Measure | Value |", "|---|---|",
                f"| Winning trades | {d['trade_win_rate']:.0%} |",
                f"| Positive days | {d['positive_day_rate']:.0%} of {d['days']} days |",
                f"| Days not negative (often sold as 'no losing day') | {d['non_negative_day_rate']:.0%} |",
            ]
            c = self.claims
            if c and c.win_rate is not None:
                L.append(f"| Claimed win rate | {c.win_rate:.0%} (counted by: {c.win_rate_basis}) |")
            if c and c.trades_per_week is not None:
                L.append(f"| Claimed trades per week | {c.trades_per_week:g} |")
            L.append("")
        if self.claims and self.claims.other:
            L += ["Other claims recorded:", ""] + [f"- {o}" for o in self.claims.other] + [""]

        L += ["## Null tests", "",
              "p = probability of doing at least as well by chance (one-sided). "
              + (f"Adjusted p accounts for {self.n_trials} registered trials (Sidak)." if self.n_trials > 1 else ""),
              "", "| Test | Observed | Null mean | Null 5%-95% | p | Adjusted p |", "|---|---|---|---|---|---|"]
        for nr, padj in zip(self.nulls, self.adjusted_p):
            L.append(f"| {nr.name} | {nr.observed:+.3f} | {nr.null_mean:+.3f} | "
                     f"{nr.null_quantile(0.05):+.3f} to {nr.null_quantile(0.95):+.3f} | {_p(nr.p_value)} | {_p(padj)} |")
        L.append("")
        if self.baselines:
            b = self.baselines
            L += [f"Same instants, fixed direction: always long {b['always_long']:+.3f} R, "
                  f"always short {b['always_short']:+.3f} R (share of long trades: {b['share_long']:.0%}).", ""]

        sc = self.stop_check
        if sc.get("stops"):
            L += ["## Right direction, wrong stop", "",
                  f"{sc['right_direction']} of {sc['stops']} stopped trades reached their target later "
                  f"within the horizon. "
                  + (f"Median adverse move before the target: {sc['median_adverse_r']:.1f} times the stop distance."
                     if sc.get("median_adverse_r") is not None else ""), ""]

        if not self.by_status.empty:
            L += ["## Trades by status", "",
                  "Skipped and drawn setups show whether the trader's own filters help; "
                  "'told' trades are chosen after the fact and never count as evidence.", "",
                  "| Status | Count | Mean result after costs |", "|---|---|---|"]
            for _, row in self.by_status.iterrows():
                m = "" if pd.isna(row["mean_net_r"]) else f"{row['mean_net_r']:+.3f} R"
                L.append(f"| {row['status']} | {int(row['count'])} | {m} |")
            L.append("")

        if not self.periods.empty:
            L += ["## Result over time", "", "| Block | From | To | Trades | Mean R |", "|---|---|---|---|---|"]
            for _, row in self.periods.iterrows():
                L.append(f"| {int(row['period'])} | {pd.Timestamp(row['start']):%Y-%m-%d} | "
                         f"{pd.Timestamp(row['end']):%Y-%m-%d} | {int(row['n'])} | {row['mean_r']:+.3f} |")
            L.append("")

        if self.confirmation:
            c = self.confirmation
            L += ["## Confirmation period (frozen recipe, new data)", "",
                  "| Measure | Value |", "|---|---|",
                  f"| Trades | {c['n']} |",
                  f"| Mean result after costs | {c['mean']:+.3f} R |",
                  f"| Random direction p | {_p(c['p_random_direction'])} |"]
            if c.get("fake_levels_p") is not None:
                L.append(f"| Fake levels p | {_p(c['fake_levels_p'])} |")
            L.append("")

        if self.notes:
            L += ["## Notes", ""] + [f"- {n}" for n in self.notes] + [""]
        L += ["## What this does not say", ""] + [f"- {c}" for c in CAVEATS] + [""]
        return "\n".join(L)

    def write(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path


def _confirmation_summary(conf, n_sims: int, seed: int) -> Optional[dict]:
    if conf is None:
        return None
    if isinstance(conf, dict):
        return conf
    taken = conf[(conf["status"] == "taken") & (conf["outcome"] != "no_data")]
    r = taken["net_r"].to_numpy(dtype=float)
    rd = random_direction_test(r, taken["flipped_net_r"].to_numpy(dtype=float), n_sims=n_sims, seed=seed)
    return {"n": int(r.size), "mean": float(np.nanmean(r)) if r.size else float("nan"),
            "p_random_direction": rd.p_value}


def reality_check(
    results: pd.DataFrame,
    *,
    title: str = "Reality Check",
    claims: Optional[Claims] = None,
    extra_nulls: Sequence[NullResult] = (),
    confirmation=None,
    n_trials: int = 1,
    n_sims: int = 10_000,
    seed: int = 0,
    min_trades: int = 30,
    alpha: float = 0.05,
    notes: Iterable[str] = (),
) -> RealityCheck:
    """Build the report from verified trades (output of ``verify_trades`` or ``LevelRecipe.run``).

    confirmation: results of the *frozen* recipe on a later period (DataFrame),
        or an already computed dict with keys n, mean, p_random_direction.
    n_trials: how many variants/tests were tried in total (from the trial log);
        p-values are adjusted for it.
    """
    res = results.copy()
    if "status" not in res:
        res["status"] = "taken"
    valid = res[res["outcome"] != "no_data"] if "outcome" in res else res
    taken = valid[valid["status"] == "taken"]
    r = taken["net_r"].to_numpy(dtype=float) if not taken.empty else np.array([])
    summary = summarize_r(r)
    gross = float(np.nanmean(taken["gross_r"])) if not taken.empty else float("nan")
    cost = float(np.nanmean(taken["cost_r"])) if not taken.empty and "cost_r" in taken else 0.0
    ci = bootstrap_mean_ci(r, seed=seed) if r.size else (float("nan"), float("nan"))
    days = win_rate_by_days(taken["entry_time"], r) if r.size else {"trades": 0}
    periods = expectancy_by_period(taken["entry_time"], r) if r.size else pd.DataFrame()

    nulls: list[NullResult] = []
    baselines: dict = {}
    if r.size and "flipped_net_r" in taken:
        flipped = taken["flipped_net_r"].to_numpy(dtype=float)
        nulls.append(random_direction_test(r, flipped, n_sims=n_sims, seed=seed))
        baselines = same_instant_baselines(r, flipped, taken["side"].tolist())
    nulls.extend(extra_nulls)
    adjusted = [sidak_adjust(nr.p_value, n_trials) for nr in nulls]

    by_status = pd.DataFrame(columns=["status", "count", "mean_net_r"])
    if "net_r" in valid and not valid.empty:
        g = valid.groupby("status")["net_r"]
        by_status = pd.DataFrame({"count": g.size(), "mean_net_r": g.mean()}).reset_index()

    stop_check: dict = {}
    if not taken.empty and "direction_right_stop_wrong" in taken:
        stops = taken[taken["outcome"] == "stop"]
        right = stops[stops["direction_right_stop_wrong"].astype(bool)]
        adv = right["adverse_before_target_r"].dropna() if "adverse_before_target_r" in right else pd.Series(dtype=float)
        stop_check = {"stops": int(len(stops)), "right_direction": int(len(right)),
                      "median_adverse_r": float(adv.median()) if len(adv) else None}

    conf = _confirmation_summary(confirmation, n_sims, seed)

    reasons, warnings = [], []
    n = summary.get("n", 0)
    if n < min_trades:
        verdict = INCONCLUSIVE
        reasons.append(f"only {n} verifiable taken trades (minimum {min_trades}): absence of evidence "
                       "is not evidence of an edge")
    else:
        if not summary["mean"] > 0:
            reasons.append(f"the mean result after costs is {summary['mean']:+.3f} R")
        if not ci[0] > 0:
            reasons.append("the 95% bootstrap interval of the mean result includes zero or less")
        for nr, padj in zip(nulls, adjusted):
            if padj > alpha:
                extra = f" after adjusting for {n_trials} trials" if n_trials > 1 else ""
                reasons.append(f"does not beat the null '{nr.name}' (p = {padj:.3f}{extra})")
        if conf is not None:
            if not conf["mean"] > 0:
                reasons.append(f"the frozen recipe loses in the confirmation period ({conf['mean']:+.3f} R)")
            elif conf["p_random_direction"] > alpha:
                reasons.append("in the confirmation period it does not beat random direction "
                               f"(p = {conf['p_random_direction']:.3f})")
        verdict = NO_EDGE if reasons else PASSED

    if claims and claims.win_rate is not None and days.get("trades"):
        measured = days["trade_win_rate"]
        if claims.win_rate - measured > 0.10:
            warnings.append(f"claimed win rate {claims.win_rate:.0%} versus {measured:.0%} measured on trades"
                            + (" (the claim counts days, not trades)" if claims.win_rate_basis == "days" else ""))
    if not periods.empty and len(periods) >= 3:
        m = periods["mean_r"].to_numpy()
        if m[0] > 0 and m[-1] < m[0] / 2:
            warnings.append(f"the mean result falls over time ({m[0]:+.2f} R in the first block, {m[-1]:+.2f} R in the last)")
    if baselines and n >= min_trades and baselines["always_long"] >= summary.get("mean", 0) - 0.02 and baselines["share_long"] > 0.6:
        warnings.append("'always long' at the same instants does as well: the result may come from a rising market")
    if stop_check.get("stops") and stop_check["right_direction"] / stop_check["stops"] >= 0.5:
        warnings.append("most stopped trades reached the target later: stops placed inside normal noise")
    told = by_status[by_status["status"] == "told"]["count"].sum() if not by_status.empty else 0
    if told:
        warnings.append(f"{int(told)} trades are only told after the fact: they are excluded from the sample")
    if "entry_traded" in taken and (~taken["entry_traded"].astype(bool)).any():
        k = int((~taken["entry_traded"].astype(bool)).sum())
        warnings.append(f"{k} entry prices were never traded in the entry bar: check times, time zone and instrument")

    return RealityCheck(title=title, verdict=verdict, reasons=reasons, warnings=warnings, summary=summary,
                        gross_mean=gross, cost_mean=cost, ci=ci, days=days, by_status=by_status,
                        periods=periods, nulls=nulls, adjusted_p=adjusted, baselines=baselines,
                        stop_check=stop_check, confirmation=conf, claims=claims, notes=list(notes),
                        n_trials=n_trials, alpha=alpha)
