"""Stage 6: join returns and build the analysis table (design doc 3.1).

Outcome labels, on forward TOTAL return (Tiingo `adjClose` is dividend- and
split-adjusted) from the formation month:

    winner_3x      cumulative total return >= +200%
    outperformer   beat the benchmark over the same window
    wipeout        cumulative total return <= -70%, or delisted near zero

Two decisions worth stating, because they are where a backtest usually lies:

1. **Delisting is an outcome, not a gap.** If a series ends before the horizon,
   the last observed price is the terminal value - that IS the delisting return.
   The name is not dropped, and it is not forward-filled to the horizon. Both of
   those mistakes flatter the result, in opposite directions.

2. **Acquisitions are wins, not disappearances.** A name that ends early at a
   high price (Activision at $94.42 on the Microsoft close) is recorded as a
   realised gain at that price. Treating it as missing would delete a class of
   winners, which is exactly the failure mode that disqualified yfinance.

`survived_full_horizon` travels with every row so any analysis can separate
"held for five years" from "position ended early", rather than having that
choice silently baked in.
"""

import argparse
import bisect
import datetime as dt
import json
import os
import statistics


def load_series(path):
    rows = json.load(open(path))
    out = []
    for r in rows:
        if r.get("adj_close") is None:
            continue
        out.append((r["date"], float(r["adj_close"]),
                    (r.get("close") or 0) * (r.get("volume") or 0)))
    out.sort()
    return out


def price_on_or_after(series, date, max_gap_days=15):
    """First observation on/after `date`, within a tolerance."""
    dates = [d for d, _, _ in series]
    i = bisect.bisect_left(dates, date)
    if i >= len(series):
        return None
    d0 = dt.date.fromisoformat(date)
    d1 = dt.date.fromisoformat(series[i][0])
    if (d1 - d0).days > max_gap_days:
        return None
    return series[i]


def price_on_or_before(series, date):
    dates = [d for d, _, _ in series]
    i = bisect.bisect_right(dates, date) - 1
    return series[i] if i >= 0 else None


def add_years(date_str, years):
    d = dt.date.fromisoformat(date_str)
    try:
        return d.replace(year=d.year + years).isoformat()
    except ValueError:                       # 29 Feb
        return d.replace(year=d.year + years, day=28).isoformat()


def outcome(series, formation_date, horizon_years, wipeout=-0.70, winner=2.00):
    """Return a dict of outcome fields, or None if unpriceable at formation."""
    entry = price_on_or_after(series, formation_date)
    if not entry or entry[1] <= 0:
        return None
    target = add_years(entry[0], horizon_years)

    exit_pt = price_on_or_after(series, target)
    survived = exit_pt is not None
    if not survived:
        # Series ended before the horizon: the last observation IS the outcome.
        exit_pt = price_on_or_before(series, target)
        if not exit_pt or exit_pt[0] <= entry[0]:
            return None

    ret = exit_pt[1] / entry[1] - 1.0
    # dollar volume around formation, as the free size/liquidity proxy
    window = [dv for d, _, dv in series
              if entry[0] <= d <= add_years(entry[0], 0) or d == entry[0]]
    near = [dv for d, _, dv in series[:200] if d >= entry[0]][:60]
    dvol = statistics.median(near) if near else (window[0] if window else 0.0)

    return {
        "entry_date": entry[0], "entry_price": round(entry[1], 6),
        "exit_date": exit_pt[0], "exit_price": round(exit_pt[1], 6),
        "forward_return": round(ret, 6),
        "survived_full_horizon": survived,
        "winner_3x": ret >= winner,
        "wipeout": ret <= wipeout,
        "dollar_volume": round(dvol, 2),
    }


def build(plan_path, prices_dir, out_path, horizons=(3, 5), benchmark="SPY"):
    plan = json.load(open(plan_path))
    bench_path = os.path.join(prices_dir, f"{benchmark}.json")
    if not os.path.exists(bench_path):
        raise SystemExit(f"benchmark {benchmark} not fetched yet")
    bench = load_series(bench_path)

    treated = {r["ticker"]: r for r in plan["treated"]}
    rows = []
    missing = []

    def emit(ticker, group, formation_date, meta):
        path = os.path.join(prices_dir, f"{ticker}.json")
        if not os.path.exists(path):
            missing.append(ticker)
            return
        series = load_series(path)
        if not series:
            missing.append(ticker)
            return
        for h in horizons:
            o = outcome(series, formation_date, h)
            if not o:
                continue
            b = outcome(bench, formation_date, h)
            bench_ret = b["forward_return"] if b else None
            rows.append({
                "ticker": ticker, "group": group, "horizon_years": h,
                "formation_date": formation_date,
                "benchmark_return": bench_ret,
                "outperformer": (None if bench_ret is None
                                 else o["forward_return"] > bench_ret),
                "excess_return": (None if bench_ret is None
                                  else round(o["forward_return"] - bench_ret, 6)),
                **o, **meta,
            })

    for t, r in treated.items():
        emit(t, "treated", r["first_mention"],
             {"n_mentions": r["n_mentions"], "n_authors": r["n_authors"],
              "entity_id": r["entity_id"]})

    # Controls are evaluated at the same formation dates as the treated set, so
    # calendar exposure is identical and cannot explain a difference. Each
    # control is assigned a formation date drawn from the treated distribution.
    import random
    rng = random.Random(20260816)
    formation_dates = [r["first_mention"] for r in plan["treated"]]
    for c in plan["controls"]:
        emit(c, "control", rng.choice(formation_dates),
             {"n_mentions": 0, "n_authors": 0, "entity_id": None})

    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n_t = len({r["ticker"] for r in rows if r["group"] == "treated"})
    n_c = len({r["ticker"] for r in rows if r["group"] == "control"})
    print(f"analysis rows: {len(rows):,}  treated={n_t} controls={n_c}")
    if missing:
        print(f"not yet priced / unavailable: {len(missing)} "
              f"({', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''})")
    print(f"-> {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("prices")
    ap.add_argument("out")
    ap.add_argument("--benchmark", default="SPY")
    a = ap.parse_args()
    build(a.plan, a.prices, a.out, benchmark=a.benchmark)
