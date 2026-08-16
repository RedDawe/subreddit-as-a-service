"""Analyses A2-A8 (design doc 6).

The governing number is LIFT: does conditioning on "the sub discussed this"
raise the density of future winners against a sensible baseline?

Two baselines are reported for every outcome, because the gap between them is
the whole point of 3.2:

  naive lift    - treated vs the raw control sample. Flatters the sub, because
                  the sub skews toward large, liquid, heavily-covered names and
                  those carry their own returns.
  adjusted lift - treated vs the SAME controls, post-stratified to the treated
                  set's size distribution. This is the number to believe.

Post-stratification replaces the doc's k=5 matched controls, which a
500-symbol/month quota cannot fund. Both estimators answer the same question -
"compare like with like on size" - one by pairing, one by reweighting. The
substitution is disclosed rather than papered over, and the naive/adjusted gap
shows how much the size skew was worth.

Confidence intervals are bootstrap percentile intervals over names (not over
name-months), so one heavily-discussed name cannot inflate the sample size.
"""

import argparse
import collections
import json
import math
import random
import statistics

N_STRATA = 5           # size quintiles; deciles are too thin at n=200 controls
N_BOOT = 2000
SEED = 20260816


# ------------------------------------------------------------------ helpers

def load(path):
    return [json.loads(l) for l in open(path)]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def strata_edges(values, n_strata=N_STRATA):
    """Quantile cut points, deduplicated.

    Edges must be derived from the POOLED treated+control sizes, not from the
    controls alone. With control-only edges, a treated name larger than every
    control still lands in the top control stratum, so the "unsupported weight"
    diagnostic reports perfect support precisely when support is worst - it
    cannot see off-support treated names at all.

    Duplicate cut points are collapsed: a degenerate size distribution would
    otherwise produce repeated edges and a silently meaningless stratification.
    """
    vals = sorted(v for v in values if v and v > 0)
    if len(vals) < n_strata:
        return []
    raw = [vals[int(len(vals) * i / n_strata)] for i in range(1, n_strata)]
    out = []
    for e in raw:
        if not out or e > out[-1]:
            out.append(e)
    return out


def stratum_of(value, edges):
    if not value or value <= 0:
        return 0
    lo = 0
    for e in edges:
        if value >= e:
            lo += 1
    return lo


def post_stratified_rate(controls, treated, label, edges):
    """P(label | control), reweighted to the treated size distribution.

    Strata with no control observations are dropped and the remaining weights
    renormalised; the share of treated weight that had no control support is
    returned so it can be reported rather than hidden.
    """
    t_w = collections.Counter(stratum_of(r["dollar_volume"], edges) for r in treated)
    total_t = sum(t_w.values())
    by_s = collections.defaultdict(list)
    for r in controls:
        by_s[stratum_of(r["dollar_volume"], edges)].append(bool(r[label]))

    num = den = 0.0
    unsupported = 0
    for s, w in t_w.items():
        obs = by_s.get(s)
        if not obs:
            unsupported += w
            continue
        num += (w / total_t) * (sum(obs) / len(obs))
        den += (w / total_t)
    if den == 0:
        return None, 1.0
    return num / den, unsupported / total_t


def bootstrap_lift(treated, controls, label, edges, n_boot=N_BOOT, seed=SEED):
    rng = random.Random(seed)
    out = []
    for _ in range(n_boot):
        t = [treated[rng.randrange(len(treated))] for _ in range(len(treated))]
        c = [controls[rng.randrange(len(controls))] for _ in range(len(controls))]
        pt = sum(bool(r[label]) for r in t) / len(t)
        pc, _ = post_stratified_rate(c, t, label, edges)
        if pc and pc > 0:
            out.append(pt / pc)
    if not out:
        return (None, None)
    out.sort()
    return (out[int(0.025 * len(out))], out[int(0.975 * len(out))])


def dedupe_by_name(rows):
    """One row per ticker (the earliest formation), so lift is per name."""
    best = {}
    for r in rows:
        k = r["ticker"]
        if k not in best or r["formation_date"] < best[k]["formation_date"]:
            best[k] = r
    return list(best.values())


# ------------------------------------------------------------------- A2

def a2_lift(rows, horizon, out=print):
    rows = [r for r in rows if r["horizon_years"] == horizon]
    treated = dedupe_by_name([r for r in rows if r["group"] == "treated"])
    controls = dedupe_by_name([r for r in rows if r["group"] == "control"])
    if not treated or not controls:
        out(f"  horizon {horizon}y: insufficient data "
            f"(treated={len(treated)}, controls={len(controls)})")
        return {}

    edges = strata_edges([r["dollar_volume"] for r in treated + controls])
    out(f"\n=== A2  LIFT, {horizon}-year horizon ===")
    out(f"  treated names : {len(treated)}")
    out(f"  control names : {len(controls)}")
    out(f"  size strata   : {N_STRATA} (dollar-volume quintiles)")
    out("")
    out(f"  {'outcome':14}{'treated':>9}{'ctrl raw':>10}{'ctrl adj':>10}"
        f"{'naive':>8}{'ADJUSTED':>10}{'95% CI':>18}")

    res = {}
    for label in ("winner_3x", "outperformer", "wipeout"):
        t_vals = [bool(r[label]) for r in treated if r[label] is not None]
        c_vals = [bool(r[label]) for r in controls if r[label] is not None]
        if not t_vals or not c_vals:
            continue
        pt = sum(t_vals) / len(t_vals)
        pc_raw = sum(c_vals) / len(c_vals)
        pc_adj, unsup = post_stratified_rate(controls, treated, label, edges)
        naive = pt / pc_raw if pc_raw > 0 else float("nan")
        adj = pt / pc_adj if pc_adj else float("nan")
        lo, hi = bootstrap_lift(treated, controls, label, edges)
        ci = f"[{lo:.2f}, {hi:.2f}]" if lo is not None else "n/a"
        out(f"  {label:14}{pt:>8.1%}{pc_raw:>10.1%}"
            f"{(pc_adj if pc_adj else 0):>10.1%}{naive:>8.2f}{adj:>10.2f}{ci:>18}")
        res[label] = {"p_treated": pt, "p_control_raw": pc_raw,
                      "p_control_adj": pc_adj, "naive_lift": naive,
                      "adjusted_lift": adj, "ci": [lo, hi],
                      "treated_ci": wilson(sum(t_vals), len(t_vals)),
                      "unsupported_weight": unsup}
        if unsup > 0.05:
            out(f"  {'':14}note: {unsup:.0%} of treated weight had no control "
                f"support in its size stratum")

    med_t = statistics.median(r["forward_return"] for r in treated)
    med_c = statistics.median(r["forward_return"] for r in controls)
    out(f"\n  median forward return  treated {med_t:+.1%}   control {med_c:+.1%}")
    surv_t = sum(r["survived_full_horizon"] for r in treated) / len(treated)
    surv_c = sum(r["survived_full_horizon"] for r in controls) / len(controls)
    out(f"  survived full horizon  treated {surv_t:.1%}   control {surv_c:.1%}")
    res["_meta"] = {"n_treated": len(treated), "n_control": len(controls),
                    "median_return_treated": med_t, "median_return_control": med_c,
                    "survival_treated": surv_t, "survival_control": surv_c}
    return res


# ------------------------------------------------------------------- A3

def a3_recall(rows, horizon, out=print):
    """Recall for winners AND losers - the denominator 1.2 insists on."""
    rows = [r for r in rows if r["horizon_years"] == horizon]
    treated = {r["ticker"] for r in rows if r["group"] == "treated"}
    allr = dedupe_by_name(rows)
    out(f"\n=== A3  RECALL, {horizon}-year horizon ===")
    out("  of names in each outcome class, what share did the sub discuss?")
    out(f"  {'class':16}{'n':>6}{'mentioned':>12}{'recall':>9}")
    res = {}
    for label, sel in (("winner_3x", lambda r: r["winner_3x"]),
                       ("wipeout", lambda r: r["wipeout"]),
                       ("outperformer", lambda r: r["outperformer"]),
                       ("all names", lambda r: True)):
        pool = [r for r in allr if sel(r)]
        if not pool:
            continue
        n = len(pool)
        k = sum(1 for r in pool if r["ticker"] in treated)
        out(f"  {label:16}{n:>6}{k:>12}{k / n:>9.1%}")
        res[label] = {"n": n, "mentioned": k, "recall": k / n}
    out("  NB: recall here is measured within the sampled universe, not the whole")
    out("      market, so read the winner/loser GAP rather than the level.")
    return res


# ------------------------------------------------------------------- A8

def a8_dose(rows, horizon, out=print):
    rows = dedupe_by_name([r for r in rows
                           if r["horizon_years"] == horizon and r["group"] == "treated"])
    out(f"\n=== A8  DOSE-RESPONSE, {horizon}-year horizon ===")
    out("  does lift rise with mention intensity? a flat curve suggests")
    out("  coincidental coverage rather than signal.")
    out(f"  {'authors':>10}{'n':>6}{'winner_3x':>12}{'wipeout':>10}{'median ret':>12}")
    buckets = [(3, 4), (5, 9), (10, 19), (20, 10**6)]
    res = {}
    for lo, hi in buckets:
        sel = [r for r in rows if lo <= r["n_authors"] <= hi]
        if len(sel) < 5:
            continue
        w = sum(bool(r["winner_3x"]) for r in sel) / len(sel)
        k = sum(bool(r["wipeout"]) for r in sel) / len(sel)
        m = statistics.median(r["forward_return"] for r in sel)
        tag = f"{lo}-{hi}" if hi < 10**6 else f"{lo}+"
        out(f"  {tag:>10}{len(sel):>6}{w:>12.1%}{k:>10.1%}{m:>+12.1%}")
        res[tag] = {"n": len(sel), "winner_3x": w, "wipeout": k, "median_return": m}
    return res


# ------------------------------------------------------------------- A7

def a7_portfolio(rows, horizon, out=print):
    """Equal- and conviction-weighted buy-and-hold vs the benchmark."""
    rows = dedupe_by_name([r for r in rows
                           if r["horizon_years"] == horizon and r["group"] == "treated"])
    out(f"\n=== A7  PORTFOLIO, {horizon}-year buy-and-hold ===")
    if not rows:
        return {}
    eq = statistics.mean(r["forward_return"] for r in rows)
    wts = [r["n_authors"] for r in rows]
    conv = (sum(r["forward_return"] * w for r, w in zip(rows, wts)) / sum(wts)
            if sum(wts) else float("nan"))
    bench = statistics.mean(r["benchmark_return"] for r in rows
                            if r["benchmark_return"] is not None)
    out(f"  equal-weighted       {eq:+.1%}")
    out(f"  author-weighted      {conv:+.1%}")
    out(f"  benchmark (SPY)      {bench:+.1%}")
    out(f"  excess (equal-wt)    {eq - bench:+.1%}")
    out("  NB: not factor-adjusted. 3.3 requires FF5+momentum alpha before this")
    out("      number means anything - a value-tilted book vs SPY over this window")
    out("      is a statement about the value factor, not about the subreddit.")
    return {"equal_weighted": eq, "author_weighted": conv, "benchmark": bench,
            "excess": eq - bench}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_table")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load(a.analysis_table)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    horizons = sorted({r["horizon_years"] for r in rows})
    results = {}
    for h in horizons:
        results[f"A2_{h}y"] = a2_lift(rows, h, emit)
        results[f"A3_{h}y"] = a3_recall(rows, h, emit)
        results[f"A8_{h}y"] = a8_dose(rows, h, emit)
        results[f"A7_{h}y"] = a7_portfolio(rows, h, emit)
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1, default=str)
        with open(a.out.replace(".json", ".txt"), "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
