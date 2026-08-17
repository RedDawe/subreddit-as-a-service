"""Export one row per company, so results can be inspected without running code.

Everything else in this repo reports aggregates. This writes the underlying
per-company table: what was discussed, how much, and what it did afterwards.
Open it in Excel, sort by any column, and check the conclusions yourself.

One row per (ticker, horizon). Columns are documented in the header comment of
artifacts/companies_README.md.
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from analyses import load                                        # noqa: E402
from rank_analysis import ranking_signals                        # noqa: E402

COLS = [
    "ticker", "group", "horizon_years",
    "n_mentions", "n_authors", "total_upvotes", "best_post_upvotes",
    "rank_by_authors", "rank_by_upvotes",
    "entry_date", "entry_price", "exit_date", "exit_price",
    "forward_return_pct", "benchmark_return_pct", "excess_vs_spy_pct",
    "tripled", "beat_spy", "lost_70pct", "survived_full_horizon",
    "dollar_volume_at_entry", "size_rank_in_sample",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_table")
    ap.add_argument("mentions")
    ap.add_argument("posts")
    ap.add_argument("out")
    a = ap.parse_args()

    rows = load(a.analysis_table)
    sig = ranking_signals(a.mentions, a.posts)

    out_rows = []
    for h in sorted({r["horizon_years"] for r in rows}):
        sel = [r for r in rows if r["horizon_years"] == h]
        # size rank across the whole sample, so a reader can see for themselves
        # how much "most discussed" overlaps with "biggest"
        by_size = sorted(sel, key=lambda r: -(r["dollar_volume"] or 0))
        size_rank = {r["ticker"]: i + 1 for i, r in enumerate(by_size)}
        treated = [r for r in sel if r["group"] == "treated"]
        by_auth = sorted(treated, key=lambda r: -sig.get(r["ticker"], {}).get("n_authors", 0))
        auth_rank = {r["ticker"]: i + 1 for i, r in enumerate(by_auth)}
        by_ups = sorted(treated, key=lambda r: -sig.get(r["ticker"], {}).get("total_score", 0))
        ups_rank = {r["ticker"]: i + 1 for i, r in enumerate(by_ups)}

        for r in sel:
            s = sig.get(r["ticker"], {})
            out_rows.append({
                "ticker": r["ticker"],
                "group": "mentioned" if r["group"] == "treated" else "not_mentioned",
                "horizon_years": h,
                "n_mentions": s.get("n_mentions", 0),
                "n_authors": s.get("n_authors", 0),
                "total_upvotes": s.get("total_score", 0),
                "best_post_upvotes": s.get("max_score", 0),
                "rank_by_authors": auth_rank.get(r["ticker"], ""),
                "rank_by_upvotes": ups_rank.get(r["ticker"], ""),
                "entry_date": r["entry_date"],
                "entry_price": round(r["entry_price"], 4),
                "exit_date": r["exit_date"],
                "exit_price": round(r["exit_price"], 4),
                "forward_return_pct": round(100 * r["forward_return"], 1),
                "benchmark_return_pct": (round(100 * r["benchmark_return"], 1)
                                         if r["benchmark_return"] is not None else ""),
                "excess_vs_spy_pct": (round(100 * r["excess_return"], 1)
                                      if r.get("excess_return") is not None else ""),
                "tripled": int(bool(r["winner_3x"])),
                "beat_spy": ("" if r["outperformer"] is None
                             else int(bool(r["outperformer"]))),
                "lost_70pct": int(bool(r["wipeout"])),
                "survived_full_horizon": int(bool(r["survived_full_horizon"])),
                "dollar_volume_at_entry": int(r["dollar_volume"] or 0),
                "size_rank_in_sample": size_rank.get(r["ticker"], ""),
            })

    out_rows.sort(key=lambda x: (x["horizon_years"], x["group"],
                                 x["rank_by_authors"] or 10**6, x["ticker"]))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out_rows)
    n_t = len({r["ticker"] for r in out_rows if r["group"] == "mentioned"})
    n_c = len({r["ticker"] for r in out_rows if r["group"] == "not_mentioned"})
    print(f"{len(out_rows)} rows ({n_t} mentioned, {n_c} not) -> {a.out}")


if __name__ == "__main__":
    main()
