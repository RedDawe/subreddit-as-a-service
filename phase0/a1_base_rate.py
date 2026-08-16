"""A1 - base-rate check (design doc 6, "run first"; gate in 7 Phase 0).

The gate: if the set of names mentioned >=2x in a rolling 12-month window is not
meaningfully narrower than the investable universe, then conditioning on "the
sub talked about it" barely narrows anything, H1 has no room to show lift, and
the project stops before any price data is bought.

Reports the funnel by cohort year, never pooled only (design doc 4.2 / 8: the
sub grew enormously post-2020, so a pooled number is really a statement about
2020-21).
"""

import collections
import datetime as dt
import json
import os
import sys

# Fallback only. Prefer the real point-in-time count from phase2/universe_pit.py:
# a fixed denominator silently misstates the funnel, because the listed universe
# is not constant (5,585 US-listed stocks in 2015 vs 8,238 in 2026). Using 5,000
# throughout overstates the funnel width in every year after ~2016.
INVESTABLE_UNIVERSE = 5000


def _pit_universe_sizes():
    """year -> count of US-listed stocks mid-year, or {} if unavailable."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase2"))
        from universe_pit import PitUniverse
        u = PitUniverse()
    except Exception:                                       # noqa: BLE001
        return {}
    out = {}
    for y in range(2010, 2027):
        try:
            out[y] = len(u.universe_at(f"{y}-06-30"))
        except Exception:                                   # noqa: BLE001
            pass
    return {y: n for y, n in out.items() if n}


def load(paths, min_conf=0.0):
    """Load one or more mention files. Submissions and comments are unioned.

    Design doc §10 asks whether comments belong in the funnel. They do - they
    carry most of the volume and most of the bear cases - so this takes a list
    rather than forcing a submissions-only view.
    """
    if isinstance(paths, str):
        paths = [paths]
    rows = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if r["confidence"] >= min_conf:
                    r["dt"] = dt.datetime.utcfromtimestamp(r["created_utc"])
                    rows.append(r)
    return rows


def funnel(rows, label=""):
    by_entity_month = collections.defaultdict(set)
    per_entity = collections.Counter()
    authors = collections.defaultdict(set)

    for r in rows:
        ym = (r["dt"].year, r["dt"].month)
        by_entity_month[r["entity_id"]].add(ym)
        per_entity[r["entity_id"]] += 1
        if r.get("author") and r["author"] != "[deleted]":
            authors[r["entity_id"]].add(r["author"])

    ever = len(per_entity)
    ge2 = sum(1 for e, n in per_entity.items() if n >= 2)
    ge5 = sum(1 for e, n in per_entity.items() if n >= 5)
    ge2_auth = sum(1 for e, a in authors.items() if len(a) >= 2)
    ge3_auth = sum(1 for e, a in authors.items() if len(a) >= 3)

    print(f"\n--- {label} ---")
    print(f"  mentions                       {len(rows):>7,}")
    print(f"  distinct entities   >=1x       {ever:>7,}   "
          f"({ever / INVESTABLE_UNIVERSE:6.1%} of ~{INVESTABLE_UNIVERSE:,} universe)")
    print(f"  distinct entities   >=2x       {ge2:>7,}   "
          f"({ge2 / INVESTABLE_UNIVERSE:6.1%})")
    print(f"  distinct entities   >=5x       {ge5:>7,}   "
          f"({ge5 / INVESTABLE_UNIVERSE:6.1%})")
    print(f"  entities >=2 distinct authors  {ge2_auth:>7,}   "
          f"({ge2_auth / INVESTABLE_UNIVERSE:6.1%})")
    print(f"  entities >=3 distinct authors  {ge3_auth:>7,}   "
          f"({ge3_auth / INVESTABLE_UNIVERSE:6.1%})")
    return {"mentions": len(rows), "ever": ever, "ge2": ge2, "ge5": ge5,
            "ge2_authors": ge2_auth, "ge3_authors": ge3_auth}


def rolling_12mo(rows, pit=None):
    """Per cohort year: names mentioned >=2x within that 12-month window."""
    pit = pit or {}
    by_year = collections.defaultdict(list)
    for r in rows:
        by_year[r["dt"].year].append(r)

    src = "point-in-time listed universe" if pit else f"fixed {INVESTABLE_UNIVERSE:,}"
    print(f"\n--- funnel width by cohort year (denominator: {src}) ---")
    print(f"  {'year':<6}{'mentions':>10}{'>=1x':>9}{'>=2x':>9}{'>=5x':>9}"
          f"{'>=3 authors':>13}{'universe':>10}{'% @>=2x':>10}")
    out = {}
    for y in sorted(by_year):
        rs = by_year[y]
        cnt = collections.Counter(r["entity_id"] for r in rs)
        auth = collections.defaultdict(set)
        for r in rs:
            if r.get("author") and r["author"] != "[deleted]":
                auth[r["entity_id"]].add(r["author"])
        e1 = len(cnt)
        e2 = sum(1 for v in cnt.values() if v >= 2)
        e5 = sum(1 for v in cnt.values() if v >= 5)
        a3 = sum(1 for v in auth.values() if len(v) >= 3)
        univ = pit.get(y, INVESTABLE_UNIVERSE)
        print(f"  {y:<6}{len(rs):>10,}{e1:>9,}{e2:>9,}{e5:>9,}{a3:>13,}"
              f"{univ:>10,}{e2 / univ:>10.1%}")
        out[y] = {"mentions": len(rs), "ge1": e1, "ge2": e2, "ge5": e5,
                  "ge3_authors": a3, "universe": univ}
    return out


def verdict(by_year, as_of_year=2026):
    """State the Phase 0 gate outcome explicitly rather than leaving it to the reader.

    Judged only on cohorts that can actually carry a forward return. A cohort
    formed in 2025 has no 5-year outcome measurable in 2026, so including it in
    the gate would fail the project on data the study could never use. Design
    doc 4.3 sets the horizons; this applies them.
    """
    for horizon, label in ((5, "5-year"), (3, "3-year")):
        last = as_of_year - horizon
        usable = {y: v for y, v in by_year.items()
                  if 2015 <= y <= last and v["mentions"] > 200}
        print(f"\nGATE ({label} horizon, cohorts <= {last}):")
        if not usable:
            print("  insufficient data to judge.")
            continue
        worst_year = max(usable, key=lambda y: usable[y]["ge2"] / usable[y].get("universe", INVESTABLE_UNIVERSE))
        worst = usable[worst_year]["ge2"]
        univ = usable[worst_year].get("universe", INVESTABLE_UNIVERSE)
        share = worst / univ
        print(f"  widest usable annual >=2x funnel is {worst:,} names in "
              f"{worst_year} ({share:.1%} of {univ:,} listed).")
        if share > 0.5:
            print("  -> FAIL. The sub is not selective; H1 has little room to show lift.")
        elif share > 0.25:
            print("  -> MARGINAL. Selective, but the candidate set is large; lift")
            print("     will need to be strong to be useful as a screener.")
        else:
            print("  -> PASS. The funnel is materially narrower than the universe,")
            print("     so lift is worth measuring.")

    newest = max(by_year)
    if by_year[newest]["ge2"] / by_year[newest].get("universe", INVESTABLE_UNIVERSE) > 0.25:
        print(f"\nNOTE: the most recent cohorts are far wider "
              f"({by_year[newest]['ge2']:,} names >=2x in {newest}). The sub now "
              "covers a\n  large fraction of the universe, so its value as a "
              "*filter* is decaying over\n  time even where the historical "
              "funnel was narrow. Worth reporting as a trend\n  in its own right.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    min_conf = 0.0
    paths = []
    for a in args:
        try:
            min_conf = float(a)
        except ValueError:
            paths.append(a)
    rows = load(paths, min_conf)
    print(f"sources: {', '.join(os.path.basename(p) for p in paths)}")
    if not rows:
        print("no mentions loaded")
        sys.exit(1)
    pit = _pit_universe_sizes()
    funnel(rows, f"all mentions (confidence >= {min_conf})")
    funnel([r for r in rows if r["channel"] == "cashtag"], "cashtag channel only (high precision)")
    by_year = rolling_12mo(rows, pit)
    verdict(by_year)
