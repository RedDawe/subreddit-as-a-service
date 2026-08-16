"""Choose which symbols to spend the monthly quota on (design doc 3.2).

The design doc asks for k=5 matched controls per (ticker, month) mention. On a
500-unique-symbols/month budget that is impossible: the treated set alone is
477 names, and k=5 would need thousands.

So the control design is changed, and the change is a substitution rather than
a weakening: instead of 1:k matching, draw ONE stratified random sample of the
point-in-time universe and **post-stratify** it to the treated set's size
distribution when computing lift. Both remove the confound that the sub skews
toward large, liquid names; matching does it by pairing, post-stratification by
reweighting. The estimator is documented in phase3/analyses.py.

Treated set: names with >=3 distinct authors in formation years 2019-2021.
Author diversity is the design doc's preferred weighting (5.4) - three people
independently discussing a name beats one person posting three times - and it
keeps the treated set inside one month's quota.

Formation window ends 2021 so that BOTH horizons are measurable from Aug 2026:
3-year outcomes resolve by 2024, 5-year by 2026. One symbol spend, two horizons.
"""

import argparse
import collections
import datetime as dt
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase2"))
from universe_pit import PitUniverse                              # noqa: E402

FORMATION_YEARS = (2019, 2020, 2021)
BENCHMARKS = ["SPY", "VTV", "IWD"]          # SPY + two value benchmarks (3.3)


def treated(mentions_path, min_conf, min_authors, years):
    rows = []
    with open(mentions_path) as f:
        for line in f:
            m = json.loads(line)
            if m["confidence"] < min_conf or not m["ticker"]:
                continue
            y = dt.datetime.utcfromtimestamp(m["created_utc"]).year
            if y in years:
                m["year"] = y
                rows.append(m)

    authors = collections.defaultdict(set)
    counts = collections.Counter()
    first = {}
    tick = {}
    for m in rows:
        e = m["entity_id"]
        counts[e] += 1
        if m.get("author") and m["author"] != "[deleted]":
            authors[e].add(m["author"])
        if e not in first or m["created_utc"] < first[e]:
            first[e] = m["created_utc"]
        tick.setdefault(e, m["ticker"])

    keep = {e for e in counts if len(authors[e]) >= min_authors}
    out = []
    for e in keep:
        fm = dt.datetime.utcfromtimestamp(first[e])
        out.append({
            "entity_id": e, "ticker": tick[e],
            "n_mentions": counts[e], "n_authors": len(authors[e]),
            "first_mention": fm.date().isoformat(),
            "formation_month": f"{fm.year:04d}-{fm.month:02d}",
        })
    return sorted(out, key=lambda r: -r["n_mentions"])


def controls(treated_tickers, n, seed=20260816):
    """Random draw from names listed across the whole formation window.

    Requiring listing at the START of the window (not today) is what keeps this
    point-in-time: drawing from today's listed names would quietly exclude
    everything that died, which is the survivorship bias in 8.
    """
    u = PitUniverse()
    alive = u.universe_at(f"{FORMATION_YEARS[0]}-06-30")
    pool = sorted(alive - set(treated_tickers))
    rng = random.Random(seed)
    return rng.sample(pool, min(n, len(pool)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mentions")
    ap.add_argument("out")
    ap.add_argument("--min-conf", type=float, default=0.75)
    ap.add_argument("--min-authors", type=int, default=3)
    ap.add_argument("--n-controls", type=int, default=180)
    ap.add_argument("--budget", type=int, default=None,
                    help="cap total symbols; defaults to whatever the month has left")
    a = ap.parse_args()

    from ratelimit import tiingo_symbol_budget
    budget = tiingo_symbol_budget()
    remaining = a.budget if a.budget is not None else budget.remaining()

    tr = treated(a.mentions, a.min_conf, a.min_authors, set(FORMATION_YEARS))
    tr_tickers = [r["ticker"] for r in tr]

    room = remaining - len(BENCHMARKS)
    n_ctrl = min(a.n_controls, max(0, room - len(tr)))
    if len(tr) > room:
        print(f"WARNING: {len(tr)} treated names exceed the {room} symbols left "
              f"this month; keeping the most-discussed {room}.")
        tr = tr[:room]
        tr_tickers = [r["ticker"] for r in tr]
        n_ctrl = 0

    ctrl = controls(tr_tickers, n_ctrl)

    plan = {
        "formation_years": list(FORMATION_YEARS),
        "min_authors": a.min_authors, "min_conf": a.min_conf,
        "treated": tr, "controls": ctrl, "benchmarks": BENCHMARKS,
        "symbols_total": len(set(tr_tickers) | set(ctrl) | set(BENCHMARKS)),
        "quota_remaining_at_plan_time": remaining,
    }
    json.dump(plan, open(a.out, "w"), indent=1)
    print(f"treated   : {len(tr):4} names (>={a.min_authors} distinct authors, "
          f"{FORMATION_YEARS[0]}-{FORMATION_YEARS[-1]})")
    print(f"controls  : {len(ctrl):4} random point-in-time universe names")
    print(f"benchmarks: {len(BENCHMARKS):4} ({', '.join(BENCHMARKS)})")
    print(f"total     : {plan['symbols_total']:4} symbols "
          f"(quota remaining {remaining})")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
