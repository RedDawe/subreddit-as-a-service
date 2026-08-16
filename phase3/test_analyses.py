"""Unit tests for the lift estimator.

Post-stratification stands in for the design doc's k=5 matched controls, so if
it is wrong the headline number is wrong and nothing else in the study would
reveal it. These tests construct cases where the true answer is known by
arithmetic.

Run: python3 phase3/test_analyses.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from analyses import (dedupe_by_name, post_stratified_rate,  # noqa: E402
                      strata_edges, stratum_of, wilson)


def row(ticker, dv, win, group="treated", horizon=5, formation="2020-01-01"):
    return {"ticker": ticker, "dollar_volume": dv, "winner_3x": win,
            "group": group, "horizon_years": horizon,
            "formation_date": formation, "forward_return": 1.0 if win else 0.0}


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("identical size distributions leave the rate unchanged")
def _():
    controls = [row(f"c{i}", 10 ** (i % 5 + 3), i % 2 == 0, "control") for i in range(100)]
    treated = [row(f"t{i}", 10 ** (i % 5 + 3), True) for i in range(50)]
    edges = strata_edges([r["dollar_volume"] for r in treated + controls])
    adj, unsup = post_stratified_rate(controls, treated, "winner_3x", edges)
    raw = sum(r["winner_3x"] for r in controls) / len(controls)
    assert abs(adj - raw) < 0.05, (adj, raw)
    assert unsup == 0


@case("reweighting recovers the truth when size drives the outcome")
def _():
    # Big names win 80% of the time, small names 20%. Controls are half/half,
    # but the treated set is ALL big. The size-adjusted control rate must move
    # toward 0.8, not stay at the raw 0.5.
    controls = ([row(f"b{i}", 1e9, i < 40, "control") for i in range(50)]
                + [row(f"s{i}", 1e3, i < 10, "control") for i in range(50)])
    treated = [row(f"t{i}", 1e9, True) for i in range(30)]
    edges = strata_edges([r["dollar_volume"] for r in treated + controls])
    raw = sum(r["winner_3x"] for r in controls) / len(controls)
    adj, _ = post_stratified_rate(controls, treated, "winner_3x", edges)
    assert abs(raw - 0.5) < 0.01, raw
    assert adj > 0.7, f"adjusted rate {adj} should approach the big-name rate 0.8"


@case("unsupported strata are reported, not silently dropped")
def _():
    # Controls occupy only the small end; the treated set sits far above them.
    controls = [row(f"c{i}", 1e3 * (1 + i), True, "control") for i in range(20)]
    treated = [row(f"t{i}", 1e12, True) for i in range(10)]
    edges = strata_edges([r["dollar_volume"] for r in treated + controls])
    adj, unsup = post_stratified_rate(controls, treated, "winner_3x", edges)
    assert unsup > 0.9, f"expected most treated weight unsupported, got {unsup}"


@case("stratum assignment is monotone in size")
def _():
    edges = [10, 100, 1000]
    assert stratum_of(1, edges) == 0
    assert stratum_of(50, edges) == 1
    assert stratum_of(500, edges) == 2
    assert stratum_of(5000, edges) == 3
    assert stratum_of(None, edges) == 0


@case("one row per name, earliest formation wins")
def _():
    rows = [row("AAA", 1e6, True, formation="2021-01-01"),
            row("AAA", 1e6, False, formation="2019-01-01"),
            row("BBB", 1e6, True)]
    out = dedupe_by_name(rows)
    assert len(out) == 2
    aaa = [r for r in out if r["ticker"] == "AAA"][0]
    assert aaa["formation_date"] == "2019-01-01"


@case("Wilson interval brackets the point estimate and stays in [0,1]")
def _():
    lo, hi = wilson(5, 50)
    assert 0 <= lo < 0.1 < hi <= 1, (lo, hi)
    lo0, hi0 = wilson(0, 30)
    assert lo0 == 0.0 and 0 < hi0 < 0.2
    assert wilson(0, 0) == (0.0, 0.0)


if __name__ == "__main__":
    failed = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)
