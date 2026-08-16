"""A4 timing, A5 novelty, A6 trivial screens, A7 factor-adjusted alpha.

Each of these is reported with the limits of the free data stated inline rather
than in a footnote, because several of them are *partially* answerable and a
partial answer presented as a whole one is worse than no answer.
"""

import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))
from analyses import dedupe_by_name, load                        # noqa: E402
from factors import load as load_factors, ols                    # noqa: E402
from outcomes import load_series                                 # noqa: E402


LOOKBACK_DAYS = 365

# --------------------------------------------------------------------- A4

def a4_timing(rows, prices_dir, horizon, out=print):
    """Was the first mention before or after the major move began?

    "Start of the move" is the trough preceding the peak. A positive lag means
    the sub started talking about the name AFTER the run-up was under way, i.e.
    it was following price rather than anticipating it.

    The window must open BEFORE the mention. An earlier version started it at
    the mention date, which forced the trough to fall on or after the mention
    and made "0% arrived late" a tautology rather than a measurement. Prices are
    fetched from 2018-01 and formation starts 2019, so a 365-day look-back is
    available for every name.
    """
    rows = dedupe_by_name([r for r in rows
                           if r["horizon_years"] == horizon and r["group"] == "treated"])
    lags = []
    for r in rows:
        path = os.path.join(prices_dir, f"{r['ticker']}.json")
        if not os.path.exists(path):
            continue
        s = load_series(path)
        lookback = (dt.date.fromisoformat(r["entry_date"])
                    - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
        window = [(d, p) for d, p, _ in s if lookback <= d <= r["exit_date"]]
        if len(window) < 60:
            continue
        peak_i = max(range(len(window)), key=lambda i: window[i][1])
        if peak_i == 0:
            continue
        trough_i = min(range(peak_i + 1), key=lambda i: window[i][1])
        gain = window[peak_i][1] / window[trough_i][1] - 1
        if gain < 0.5:                       # no "major move" to speak of
            continue
        d_first = dt.date.fromisoformat(r["entry_date"])
        d_trough = dt.date.fromisoformat(window[trough_i][0])
        lags.append(((d_first - d_trough).days, r["ticker"], gain))

    out(f"\n=== A4  TIMING, {horizon}-year horizon ===")
    if len(lags) < 10:
        out(f"  too few names with a major move ({len(lags)}) to characterise.")
        return {}
    vals = sorted(l for l, _, _ in lags)
    after = sum(1 for v in vals if v > 0) / len(vals)
    out(f"  names with a >=50% move : {len(vals)}")
    out(f"  first mention AFTER the move began : {after:.1%}")
    out(f"  lag days  median {statistics.median(vals):+.0f}   "
        f"p25 {vals[len(vals)//4]:+.0f}   p75 {vals[3*len(vals)//4]:+.0f}")
    out("  positive = the sub discussed it only after the run-up started.")
    return {"n": len(vals), "share_after": after,
            "median_lag_days": statistics.median(vals)}


# --------------------------------------------------------------------- A5

def a5_novelty(rows, horizon, out=print):
    """Does the sub surface names a trivial screen would miss?

    Three legs, with very different evidential status:

      size      - dollar-volume quintiles of the sampled universe. Solid.
      S&P 500   - from a CURRENT constituent snapshot, so historical membership
                  is undercounted: a 2021 member since removed looks like a
                  non-member. That inflates measured novelty, i.e. it flatters
                  the sub on the hypothesis §1.3 expects to fail. Reported as a
                  bound, not a point estimate.
      non-US    - NOT reported. Entity resolution is SEC-based, so foreign-only
                  listings cannot be extracted and 0% would be an artifact.
    """
    rows = [r for r in rows if r["horizon_years"] == horizon]
    treated = dedupe_by_name([r for r in rows if r["group"] == "treated"])
    controls = dedupe_by_name([r for r in rows if r["group"] == "control"])
    out(f"\n=== A5  NOVELTY, {horizon}-year horizon ===")
    if not treated or not controls:
        out("  insufficient data.")
        return {}

    universe_dv = sorted((r["dollar_volume"] for r in treated + controls
                          if r["dollar_volume"]), reverse=True)
    if not universe_dv:
        out("  no volume data.")
        return {}
    p80 = universe_dv[int(len(universe_dv) * 0.20)]
    p50 = universe_dv[int(len(universe_dv) * 0.50)]

    big = sum(1 for r in treated if (r["dollar_volume"] or 0) >= p80)
    mid = sum(1 for r in treated if (r["dollar_volume"] or 0) >= p50)
    out(f"  treated names in the sampled universe's top quintile by dollar "
        f"volume: {big/len(treated):.1%}")
    out(f"  treated names above the median: {mid/len(treated):.1%}")
    out(f"  (controls are 20% / 50% by construction)")
    res = {"share_top_quintile": big / len(treated),
           "share_above_median": mid / len(treated)}

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase2"))
        from sp500 import fetch as sp_fetch, in_index_at
        members = sp_fetch()
        conf_in = sum(1 for r in treated
                      if in_index_at(members, r["ticker"], r["formation_date"]) is True)
        unknown = sum(1 for r in treated
                      if in_index_at(members, r["ticker"], r["formation_date"]) is None)
        n = len(treated)
        out(f"  confidently IN the S&P 500 at formation : {conf_in/n:.1%}")
        out(f"  not confidently in (upper bound on novelty): {(n-conf_in)/n:.1%}")
        out(f"    of which membership is simply unknown  : {unknown/n:.1%}")
        out("  NB the constituent list is a CURRENT snapshot, so a 2021 member")
        out("     since removed reads as a non-member. Treat the novelty share as")
        out("     an UPPER BOUND - the bias runs toward flattering the sub here.")
        res.update({"sp500_confirmed_in": conf_in / n,
                    "novelty_upper_bound": (n - conf_in) / n,
                    "sp500_unknown": unknown / n})
    except Exception as e:                                   # noqa: BLE001
        out(f"  S&P 500 leg unavailable: {type(e).__name__}")

    out("  H3's non-US leg is NOT reported: entity resolution is SEC-based, so")
    out("    foreign-only listings cannot be extracted and 0% would be an artifact.")
    return res


# --------------------------------------------------------------------- A6

def a6_trivial_screens(rows, horizon, out=print):
    """Head-to-head against the cheapest screen a reader could run for free.

    Only baseline 1 of 3.2's three is reproducible on free data: "just buy the
    big liquid names". Baselines 2 (news coverage) and 3 (a mechanical P/B or
    EV/EBIT screen) need fundamentals this tier does not carry, and are marked
    not-run rather than approximated.
    """
    rows = [r for r in rows if r["horizon_years"] == horizon]
    treated = dedupe_by_name([r for r in rows if r["group"] == "treated"])
    controls = dedupe_by_name([r for r in rows if r["group"] == "control"])
    out(f"\n=== A6  VS TRIVIAL SCREENS, {horizon}-year horizon ===")
    if not treated or not controls:
        out("  insufficient data.")
        return {}
    dv = sorted((r["dollar_volume"] for r in controls if r["dollar_volume"]),
                reverse=True)
    if not dv:
        return {}
    cut = dv[int(len(dv) * 0.20)]
    screen = [r for r in controls if (r["dollar_volume"] or 0) >= cut]
    if len(screen) < 10:
        out("  large-cap screen too small to compare.")
        return {}
    res = {}
    out(f"  {'outcome':16}{'sub':>10}{'big-liquid screen':>20}{'ratio':>9}")
    for label in ("winner_3x", "outperformer", "wipeout"):
        t = [bool(r[label]) for r in treated if r[label] is not None]
        s = [bool(r[label]) for r in screen if r[label] is not None]
        if not t or not s:
            continue
        pt, ps = sum(t) / len(t), sum(s) / len(s)
        ratio = pt / ps if ps > 0 else float("nan")
        out(f"  {label:16}{pt:>10.1%}{ps:>20.1%}{ratio:>9.2f}")
        res[label] = {"sub": pt, "screen": ps, "ratio": ratio}
    out("  baseline 2 (news coverage) and baseline 3 (mechanical value screen)")
    out("    NOT RUN - both need fundamentals the free tier does not carry.")
    return res


# --------------------------------------------------------------------- A7

def a7_factor_alpha(rows, prices_dir, horizon, out=print):
    """Factor-adjusted alpha for an equal-weighted portfolio of the treated set.

    Builds a monthly equal-weighted return series across every treated name
    that is live in that month, then regresses excess return on FF5 + momentum.
    Names that die mid-horizon simply leave the portfolio, which is the honest
    treatment - their loss is already in the month they died.
    """
    treated = dedupe_by_name([r for r in rows
                              if r["horizon_years"] == horizon and r["group"] == "treated"])
    monthly = collections.defaultdict(list)
    for r in treated:
        path = os.path.join(prices_dir, f"{r['ticker']}.json")
        if not os.path.exists(path):
            continue
        s = load_series(path)
        by_m = {}
        for d, p, _ in s:
            if r["entry_date"] <= d <= r["exit_date"]:
                by_m[d[:7]] = p              # last close of each month
        months = sorted(by_m)
        for a, b in zip(months, months[1:]):
            monthly[b].append(by_m[b] / by_m[a] - 1.0)

    ff = load_factors()
    keys = sorted(k for k in monthly if k in ff and len(monthly[k]) >= 5)
    out(f"\n=== A7  FACTOR-ADJUSTED ALPHA, {horizon}-year horizon ===")
    if len(keys) < 24:
        out(f"  only {len(keys)} usable months - too few to regress.")
        return {}

    names = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    if "Mom" in ff[keys[-1]]:
        names.append("Mom")
    y, X = [], []
    for k in keys:
        port = statistics.mean(monthly[k])
        y.append(port - ff[k]["RF"])
        X.append([ff[k][n] for n in names])
    alpha, betas = ols(y, X)
    if alpha is None:
        out("  regression failed (singular design matrix).")
        return {}

    resid = [y[i] - alpha - sum(b * x for b, x in zip(betas, X[i]))
             for i in range(len(y))]
    se = (statistics.pstdev(resid) / (len(resid) ** 0.5)) if len(resid) > 1 else 0
    t = alpha / se if se else float("nan")

    out(f"  months regressed : {len(keys)}  ({keys[0]} .. {keys[-1]})")
    out(f"  monthly alpha    : {alpha:+.4%}   (annualised {(1+alpha)**12-1:+.2%})")
    out(f"  t-stat (approx)  : {t:+.2f}")
    for n, b in zip(names, betas):
        out(f"    beta {n:8} {b:+.3f}")
    out("  NB: t-stat uses iid residual SE - no Newey-West correction, so treat")
    out("      significance as indicative rather than final.")
    return {"months": len(keys), "alpha_monthly": alpha,
            "alpha_annual": (1 + alpha) ** 12 - 1, "t_stat": t,
            "betas": dict(zip(names, betas))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_table")
    ap.add_argument("prices")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load(a.analysis_table)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    res = {}
    for h in sorted({r["horizon_years"] for r in rows}):
        res[f"A4_{h}y"] = a4_timing(rows, a.prices, h, emit)
        res[f"A5_{h}y"] = a5_novelty(rows, h, emit)
        res[f"A6_{h}y"] = a6_trivial_screens(rows, h, emit)
        res[f"A7_{h}y"] = a7_factor_alpha(rows, a.prices, h, emit)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1, default=str)
        with open(a.out.replace(".json", ".txt"), "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
