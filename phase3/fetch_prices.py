"""Fetch the planned symbols' price history. Resumable, quota-aware.

Tiingo's free tier allows 50 requests/hour, so a 470-symbol plan takes about ten
hours of wall clock. This container is ephemeral, so the job writes one file per
symbol and skips anything already on disk: re-running continues rather than
restarting, and a symbol already fetched costs nothing (it is not re-claimed
against the monthly unique-symbol budget either, since the file short-circuits
before the adapter is called).

Window: 2018-01-01 to today. That covers a 2019 formation month minus a year of
run-up context (needed for A4's timing question) through a 2021 cohort's 5-year
outcome.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase2"))
from prices import PriceUnavailable, Tiingo                       # noqa: E402
from ratelimit import tiingo_symbol_budget                        # noqa: E402

START = "2018-01-01"
END = "2026-08-16"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("outdir")
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    a = ap.parse_args()

    plan = json.load(open(a.plan))
    # Benchmarks FIRST: every outcome is defined relative to them, so the
    # analysis table cannot be built at all until they exist. Fetching them last
    # means a part-finished run yields nothing.
    # Benchmarks first, then treated and controls INTERLEAVED in proportion.
    # Fetching all treated before any control means a part-finished run has no
    # comparison group and can produce no lift estimate at all - and the treated
    # set is ordered by mention count, so the partial sample would be the most
    # discussed names, i.e. maximally unrepresentative.
    tre = [r["ticker"] for r in plan["treated"]]
    ctl = list(plan["controls"])
    ratio = max(1, round(len(tre) / max(1, len(ctl))))
    mixed, ti, ci = [], 0, 0
    while ti < len(tre) or ci < len(ctl):
        for _ in range(ratio):
            if ti < len(tre):
                mixed.append(tre[ti]); ti += 1
        if ci < len(ctl):
            mixed.append(ctl[ci]); ci += 1
    symbols = plan["benchmarks"] + mixed
    # de-dupe, preserving order so the most-discussed treated names land first;
    # if the quota runs out mid-run, the important half is already on disk.
    seen, ordered = set(), []
    for s in symbols:
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)

    os.makedirs(a.outdir, exist_ok=True)
    adapter = Tiingo()
    budget = tiingo_symbol_budget()

    done = miss = fail = 0
    for i, sym in enumerate(ordered, 1):
        path = os.path.join(a.outdir, f"{sym.replace('/', '_')}.json")
        if os.path.exists(path):
            done += 1
            continue
        try:
            rows = adapter.history_full(sym, a.start, a.end)
        except PriceUnavailable as e:
            print(f"[{i}/{len(ordered)}] STOP {sym}: {e}", flush=True)
            break
        except Exception as e:                                    # noqa: BLE001
            print(f"[{i}/{len(ordered)}] ERROR {sym}: {type(e).__name__} {e}",
                  flush=True)
            fail += 1
            time.sleep(5)
            continue
        json.dump(rows, open(path, "w"))
        if rows:
            done += 1
        else:
            miss += 1                       # symbol unknown to Tiingo (404)
        print(f"[{i}/{len(ordered)}] {sym} {len(rows)} rows "
              f"(quota left {budget.remaining()})", flush=True)

    print(f"DONE fetched={done} empty={miss} errors={fail} "
          f"quota_remaining={budget.remaining()}")


if __name__ == "__main__":
    main()
