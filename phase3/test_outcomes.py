"""Unit tests for the outcome logic - the most error-prone code in the study.

The failure modes these guard against are the ones that silently produce a
beautiful, wrong backtest:

  * a delisted name being dropped instead of realised at its last price
  * an acquisition being treated as a disappearance rather than a gain
  * a series forward-filled to the horizon it never reached

Run: python3 phase3/test_outcomes.py
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from outcomes import add_years, outcome, price_on_or_after  # noqa: E402


def daily(start, end, fn):
    """Weekday-only series of (date, adj_close, dollar_volume)."""
    out, d = [], dt.date.fromisoformat(start)
    stop = dt.date.fromisoformat(end)
    while d <= stop:
        if d.weekday() < 5:
            out.append((d.isoformat(), fn(d), 1e6))
        d += dt.timedelta(days=1)
    return out


def linear(start, p0, per_day):
    d0 = dt.date.fromisoformat(start)
    return lambda d: max(0.01, p0 + per_day * (d - d0).days)


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("a clean 3x is labelled a winner")
def _():
    s = daily("2019-01-01", "2026-01-01", linear("2019-06-03", 100.0, 0.20))
    o = outcome(s, "2019-06-03", 5)
    assert o["forward_return"] > 2.0, o["forward_return"]
    assert o["winner_3x"] and not o["wipeout"]
    assert o["survived_full_horizon"]


@case("a name that dies mid-horizon is realised at its last price, not dropped")
def _():
    s = daily("2019-01-01", "2022-03-01", linear("2019-06-03", 100.0, -0.11))
    o = outcome(s, "2019-06-03", 5)
    assert o is not None, "a dead name must still produce an outcome"
    assert o["wipeout"], o["forward_return"]
    assert not o["survived_full_horizon"]
    assert o["exit_date"] == "2022-03-01", o["exit_date"]


@case("an acquisition is a realised gain, not a disappearance")
def _():
    s = daily("2019-01-01", "2022-03-01", linear("2019-06-03", 100.0, 0.05))
    o = outcome(s, "2019-06-03", 5)
    assert o["forward_return"] > 0, o["forward_return"]
    assert not o["survived_full_horizon"]
    assert not o["wipeout"]


@case("a series is never forward-filled past its end")
def _():
    s = daily("2019-01-01", "2022-03-01", linear("2019-06-03", 100.0, 0.05))
    o = outcome(s, "2019-06-03", 5)
    assert o["exit_date"] <= "2022-03-01"


@case("no price at formation yields no row rather than a guess")
def _():
    s = daily("2022-01-01", "2026-01-01", lambda d: 50.0)
    assert outcome(s, "2019-06-03", 5) is None


@case("formation snaps forward only within tolerance")
def _():
    s = daily("2019-01-01", "2026-01-01", lambda d: 50.0)
    assert price_on_or_after(s, "2019-06-03") is not None
    # a 6-month hole must NOT silently snap to the far side
    gapped = [r for r in s if not ("2019-07-01" <= r[0] <= "2019-12-31")]
    assert price_on_or_after(gapped, "2019-08-01") is None


@case("leap-day formation does not crash")
def _():
    assert add_years("2020-02-29", 5) == "2025-02-28"


@case("both horizons resolve from one series")
def _():
    s = daily("2019-01-01", "2026-01-01", linear("2019-06-03", 100.0, 0.10))
    o3, o5 = outcome(s, "2019-06-03", 3), outcome(s, "2019-06-03", 5)
    assert o3 and o5 and o5["forward_return"] > o3["forward_return"]


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
