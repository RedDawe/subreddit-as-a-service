"""A9 - does RANK beat membership? (not in the design doc; added after A2)

A2 tests a binary treatment: was the name mentioned at all. That is the design
doc's H1, and it came back null. But it is not how anyone actually uses a forum.
A reader scrolling r/ValueInvesting sees the names that come up *most*, on the
posts that get *upvoted*. That is a ranking, not a membership test, and it has
two properties the binary version lacks:

  * it shrinks the candidate set to whatever size you choose, so the funnel-width
    problem that made A1 marginal (28-41% of the universe) stops mattering;
  * it is available in the recent years the horizon locks out of A2. You cannot
    measure a 2025 cohort's 5-year return, but you can still rank 2025 names.

So this asks: among names the sub discussed, does ranking them by discussion
intensity separate outcomes? Four ranking signals, all computable from the panel:

    n_mentions      raw volume
    n_authors       distinct people (the doc's preferred weighting, 5.4)
    total_score     summed post score - "what got upvoted"
    max_score       the single best-received post

Note this is a *conditional* question. A2 asks whether the sub beats the market;
A9 asks whether the sub's own ranking beats the sub's own average. Both matter,
and A9 can be positive while A2 is null - that would mean the sub is useful only
if you read the ranking, not the membership.
"""

import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))
from analyses import (bootstrap_lift, dedupe_by_name, load,  # noqa: E402
                      post_stratified_rate, strata_edges)

FORMATION_YEARS = (2019, 2020, 2021)

# Minimum number of *events* among matched controls before a ratio is reported.
# Below this the denominator is too thin for the ratio to mean anything.
MIN_CONTROL_EVENTS = 5


def _matched_event_count(controls, treated, label, edges):
    """How many control observations with label=True fall in strata the treated occupy."""
    from analyses import stratum_of
    occupied = {stratum_of(r["dollar_volume"], edges) for r in treated}
    return sum(1 for r in controls
               if bool(r[label]) and stratum_of(r["dollar_volume"], edges) in occupied)


def ranking_signals(mentions_path, posts_path, min_conf=0.75):
    """ticker -> {n_mentions, n_authors, total_score, max_score}."""
    score_of = {}
    with open(posts_path) as f:
        for line in f:
            d = json.loads(line)
            score_of[d["id"]] = d.get("score") or 0

    agg = collections.defaultdict(
        lambda: {"n_mentions": 0, "authors": set(), "total_score": 0, "max_score": 0,
                 "docs": set()})
    with open(mentions_path) as f:
        for line in f:
            m = json.loads(line)
            if m["confidence"] < min_conf or not m.get("ticker"):
                continue
            y = dt.datetime.utcfromtimestamp(m["created_utc"]).year
            if y not in FORMATION_YEARS:
                continue
            a = agg[m["ticker"]]
            a["n_mentions"] += 1
            if m.get("author") and m["author"] != "[deleted]":
                a["authors"].add(m["author"])
            if m["doc_id"] not in a["docs"]:
                a["docs"].add(m["doc_id"])
                s = score_of.get(m["doc_id"], 0)
                a["total_score"] += s
                a["max_score"] = max(a["max_score"], s)
    return {t: {"n_mentions": v["n_mentions"], "n_authors": len(v["authors"]),
                "total_score": v["total_score"], "max_score": v["max_score"]}
            for t, v in agg.items()}


def report(rows, signals, horizon, controls, out=print):
    treated = dedupe_by_name([r for r in rows
                              if r["horizon_years"] == horizon and r["group"] == "treated"])
    for r in treated:
        r.update(signals.get(r["ticker"], {}))

    out(f"\n=== A9  RANK vs MEMBERSHIP, {horizon}-year horizon ===")
    out(f"  treated names ranked: {len(treated)}")
    c_win = sum(bool(r["winner_3x"]) for r in controls) / len(controls)
    c_wipe = sum(bool(r["wipeout"]) for r in controls) / len(controls)
    c_med = statistics.median(r["forward_return"] for r in controls)
    out(f"  control baseline: winner {c_win:.1%}  wipeout {c_wipe:.1%}  "
        f"median {c_med:+.1%}")

    results = {}
    out("  adjW / adjK = SIZE-ADJUSTED lift vs controls reweighted to the")
    out("  bucket's own size distribution.  * = >20% of bucket weight off-support.")
    for sig in ("n_authors", "n_mentions", "total_score", "max_score"):
        ranked = sorted((r for r in treated if r.get(sig) is not None),
                        key=lambda r: -r.get(sig, 0))
        if len(ranked) < 40:
            continue
        out(f"\n  --- ranked by {sig} ---")
        out(f"  {'bucket':14}{'n':>5}{'winner_3x':>11}{'wipeout':>10}"
            f"{'median ret':>12}{'adjW':>9}{'adjK':>9}  {'95% CI (W)'}")
        res = {}
        for label, sel in (("top 10", ranked[:10]), ("top 25", ranked[:25]),
                           ("top 50", ranked[:50]),
                           ("rest", ranked[50:])):
            if len(sel) < 5:
                continue
            w = sum(bool(r["winner_3x"]) for r in sel) / len(sel)
            k = sum(bool(r["wipeout"]) for r in sel) / len(sel)
            m = statistics.median(r["forward_return"] for r in sel)
            # The whole point of the size adjustment: the most-discussed names
            # are the biggest names, and megacaps did very well over this
            # window. Without reweighting the controls to each bucket's own size
            # distribution, "top 10 beat the market" may be nothing but "large
            # caps beat the market", which is not a fact about the subreddit.
            # Ratio estimates explode when the matched control cell contains
            # almost no events: a top-10 bucket of megacaps matches into a
            # stratum where perhaps one control 3x'd, and the lift prints as 60
            # with an interval running to 190. That is an artifact of a tiny
            # denominator, not a finding, so it is suppressed rather than shown.
            edges = strata_edges([r["dollar_volume"] for r in sel + controls])
            cw, unsup = post_stratified_rate(controls, sel, "winner_3x", edges)
            ck, _ = post_stratified_rate(controls, sel, "wipeout", edges)
            n_ctrl_events = _matched_event_count(controls, sel, "winner_3x", edges)
            if n_ctrl_events >= MIN_CONTROL_EVENTS and cw:
                lift_w = f"{w / cw:.2f}"
                lo, hi = bootstrap_lift(sel, controls, "winner_3x", edges, n_boot=800)
                ci = f"[{lo:.2f},{hi:.2f}]" if lo is not None else "n/a"
            else:
                lift_w, ci = "unstable", f"(only {n_ctrl_events} matched ctrl winners)"
                lo = hi = None
            lift_k = f"{k / ck:.2f}" if ck else "-"
            flag = " *" if unsup > 0.20 else ""
            out(f"  {label:14}{len(sel):>5}{w:>11.1%}{k:>10.1%}{m:>+12.1%}"
                f"{lift_w:>10}{lift_k:>8}  {ci}{flag}")
            res[label] = {"n": len(sel), "winner_3x": w, "wipeout": k,
                          "median_return": m, "excess_vs_control": m - c_med,
                          "size_adj_winner_lift": lift_w,
                          "size_adj_wipeout_lift": lift_k,
                          "winner_lift_ci": [lo, hi],
                          "matched_control_winners": n_ctrl_events,
                          "unsupported_weight": unsup}
        results[sig] = res
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_table")
    ap.add_argument("mentions")
    ap.add_argument("posts")
    ap.add_argument("--out")
    a = ap.parse_args()

    rows = load(a.analysis_table)
    signals = ranking_signals(a.mentions, a.posts)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    res = {}
    for h in sorted({r["horizon_years"] for r in rows}):
        ctrl = dedupe_by_name([r for r in rows
                               if r["horizon_years"] == h and r["group"] == "control"])
        if ctrl:
            res[f"A9_{h}y"] = report(rows, signals, h, ctrl, emit)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1, default=str)
        with open(a.out.replace(".json", ".txt"), "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
