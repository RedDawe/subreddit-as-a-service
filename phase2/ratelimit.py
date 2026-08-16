"""Persistent rate-limit and quota budgets for the free data tiers.

The limits that matter here are not per-process, they are per-account and reset
on wall-clock boundaries. A limiter that only lives inside one run would happily
burn a whole month's symbol quota across three runs and never notice, so the
state is kept on disk and survives restarts (this container is ephemeral; the
quota is not).

Free-tier limits, taken from the vendors' own pricing/knowledge-base pages
(2026-08):

  Tiingo   50 requests/hour, 1000 requests/day, 1 GB/month,
           500 UNIQUE SYMBOLS per month   <- the binding constraint
  Massive  5 requests/minute (free "Basic"), and a rolling ~2-year history
           window, which makes it unusable for this study's horizons

The unique-symbol cap is the one that shapes the study: 500/month against a
4,316-entity mention universe means symbols must be spent deliberately, not
looped over. `SymbolBudget.remaining()` is meant to be consulted before
planning a batch, not discovered halfway through one.
"""

import datetime as dt
import json
import os
import threading
import time

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DEFAULT_STATE = os.path.join(STATE_DIR, "ratelimit_state.json")

_FILE_LOCK = threading.Lock()


def _read_state(path):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except (ValueError, OSError):
            pass
    return {}


def _update_state(path, key, mutate):
    """Read-modify-write the shared state file under `key`.

    The limiter and the symbol budget both persist into one file. Each holding
    its own in-memory copy and writing it wholesale means whichever saves last
    silently erases the other's node - which is exactly what happened: six
    claimed symbols vanished because `limiter.wait()` saved after
    `budget.claim()` did. Every write therefore re-reads first.
    """
    with _FILE_LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = _read_state(path)
        node = mutate(state.setdefault(key, {}))
        if node is not None:
            state[key] = node
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, path)
        return state[key]


class RateLimiter:
    """Sliding-window limiter with several simultaneous windows.

    windows: list of (max_calls, period_seconds). A call must satisfy all of
    them, so Tiingo's 50/hour and 1000/day are enforced together.
    """

    def __init__(self, name, windows, state_path=DEFAULT_STATE):
        self.name = name
        self.windows = windows
        self.state_path = state_path
        self._lock = threading.Lock()
        self._announced = False
        os.makedirs(os.path.dirname(state_path), exist_ok=True)

    def _current_calls(self):
        horizon = max(p for _, p in self.windows)
        now = time.time()
        node = _read_state(self.state_path).get(self.name, {})
        return [t for t in node.get("calls", []) if now - t < horizon]

    def wait(self):
        """Block until a call is permitted, then record it."""
        with self._lock:
            while True:
                now = time.time()
                calls = self._current_calls()
                sleep_for = 0.0
                for limit, period in self.windows:
                    recent = [t for t in calls if now - t < period]
                    if len(recent) >= limit:
                        # wait until the oldest call in this window ages out
                        sleep_for = max(sleep_for, period - (now - min(recent)) + 0.5)
                if sleep_for > 0 and not self._announced:
                    import sys
                    print(f"  [ratelimit:{self.name}] waiting {sleep_for/60:.1f} min "
                          f"({len(calls)} calls in window)", file=sys.stderr, flush=True)
                    self._announced = True
                if sleep_for <= 0:
                    self._announced = False
                    def mutate(node, _calls=calls, _now=now):
                        node["calls"] = _calls + [_now]
                        return node
                    _update_state(self.state_path, self.name, mutate)
                    return
                time.sleep(min(sleep_for, 60))


class SymbolBudget:
    """Tracks unique symbols consumed in the current calendar month."""

    def __init__(self, name, limit, state_path=DEFAULT_STATE):
        self.name = name
        self.limit = limit
        self.state_path = state_path
        os.makedirs(os.path.dirname(state_path), exist_ok=True)

    @staticmethod
    def _fresh(node):
        """Reset the node if the calendar month rolled over."""
        month = dt.datetime.utcnow().strftime("%Y-%m")
        if node.get("month") != month:
            node.clear()
            node["month"] = month
            node["symbols"] = []
        node.setdefault("symbols", [])
        return node

    def used(self):
        node = self._fresh(dict(_read_state(self.state_path).get(self.name, {})))
        return set(node["symbols"])

    def remaining(self):
        return max(0, self.limit - len(self.used()))

    def would_cost(self, symbols):
        """How many NEW symbols a batch would consume (already-seen ones are free)."""
        return len(set(s.upper() for s in symbols) - self.used())

    def claim(self, symbol):
        """Record a symbol. Returns False if it would exceed the monthly cap."""
        s = symbol.upper()
        outcome = {}

        def mutate(node):
            self._fresh(node)
            seen = set(node["symbols"])
            if s in seen:
                outcome["ok"] = True
            elif len(seen) >= self.limit:
                outcome["ok"] = False
            else:
                node["symbols"].append(s)
                outcome["ok"] = True
            return node

        _update_state(self.state_path, self.name, mutate)
        return outcome["ok"]


# Vendor presets
def tiingo_limiter(state_path=DEFAULT_STATE):
    # 50/hour and 1000/day enforced simultaneously.
    return RateLimiter("tiingo", [(50, 3600), (1000, 86400)], state_path)


def tiingo_symbol_budget(state_path=DEFAULT_STATE):
    return SymbolBudget("tiingo_symbols", 500, state_path)


def massive_limiter(state_path=DEFAULT_STATE):
    # 5 requests/minute on the free Basic plan.
    return RateLimiter("massive", [(5, 60)], state_path)


if __name__ == "__main__":
    b = tiingo_symbol_budget()
    print(f"tiingo unique symbols used this month: {len(b.used())}/{b.limit} "
          f"(remaining {b.remaining()})")
