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
import sys

# Rough count of US exchange-listed operating companies. The design doc frames
# the comparison against "5,000+ listed companies"; SEC's exchange file carries
# ~10.4k rows including share classes, funds and trusts, so this is the honest
# order of magnitude for a stock-picker's investable universe.
INVESTABLE_UNIVERSE = 5000


def load(path, min_conf=0.0):
    rows = []
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


def rolling_12mo(rows):
    """Per cohort year: names mentioned >=2x within that 12-month window."""
    by_year = collections.defaultdict(list)
    for r in rows:
        by_year[r["dt"].year].append(r)

    print("\n--- funnel width by cohort year (12-month windows) ---")
    print(f"  {'year':<6}{'mentions':>10}{'>=1x':>9}{'>=2x':>9}{'>=5x':>9}"
          f"{'>=3 authors':>13}{'% univ @>=2x':>14}")
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
        print(f"  {y:<6}{len(rs):>10,}{e1:>9,}{e2:>9,}{e5:>9,}{a3:>13,}"
              f"{e2 / INVESTABLE_UNIVERSE:>13.1%}")
        out[y] = {"mentions": len(rs), "ge1": e1, "ge2": e2, "ge5": e5, "ge3_authors": a3}
    return out


def verdict(by_year):
    """State the Phase 0 gate outcome explicitly rather than leaving it to the reader."""
    recent = {y: v for y, v in by_year.items() if 2015 <= y <= 2024 and v["mentions"] > 200}
    if not recent:
        print("\nGATE: insufficient data to judge.")
        return
    worst = max(v["ge2"] for v in recent.values())
    share = worst / INVESTABLE_UNIVERSE
    print(f"\nGATE: widest annual >=2x funnel is {worst:,} names "
          f"({share:.1%} of the ~{INVESTABLE_UNIVERSE:,}-name universe).")
    if share > 0.5:
        print("  -> FAIL. The sub is not selective; H1 has little room to show lift.")
    elif share > 0.25:
        print("  -> MARGINAL. Selective, but the candidate set is large; lift will")
        print("     need to be strong to be useful as a screener.")
    else:
        print("  -> PASS. The funnel is materially narrower than the universe,")
        print("     so lift is worth measuring. Proceed to Phase 1 validation.")


if __name__ == "__main__":
    path = sys.argv[1]
    min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    rows = load(path, min_conf)
    if not rows:
        print("no mentions loaded")
        sys.exit(1)
    funnel(rows, f"all mentions (confidence >= {min_conf})")
    funnel([r for r in rows if r["channel"] == "cashtag"], "cashtag channel only (high precision)")
    by_year = rolling_12mo(rows)
    verdict(by_year)
