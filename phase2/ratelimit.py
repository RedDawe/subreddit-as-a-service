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
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        self._state = self._load()

    def _load(self):
        if os.path.exists(self.state_path):
            try:
                return json.load(open(self.state_path))
            except (ValueError, OSError):
                pass
        return {}

    def _save(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._state, f)
        os.replace(tmp, self.state_path)

    def _calls(self):
        return self._state.setdefault(self.name, {}).setdefault("calls", [])

    def wait(self):
        """Block until a call is permitted, then record it."""
        with self._lock:
            while True:
                now = time.time()
                calls = [t for t in self._calls() if now - t < max(p for _, p in self.windows)]
                sleep_for = 0.0
                for limit, period in self.windows:
                    recent = [t for t in calls if now - t < period]
                    if len(recent) >= limit:
                        # wait until the oldest call in this window ages out
                        sleep_for = max(sleep_for, period - (now - min(recent)) + 0.5)
                if sleep_for <= 0:
                    calls.append(now)
                    self._state[self.name]["calls"] = calls
                    self._save()
                    return
                time.sleep(min(sleep_for, 60))


class SymbolBudget:
    """Tracks unique symbols consumed in the current calendar month."""

    def __init__(self, name, limit, state_path=DEFAULT_STATE):
        self.name = name
        self.limit = limit
        self.state_path = state_path
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        self._state = {}
        if os.path.exists(state_path):
            try:
                self._state = json.load(open(state_path))
            except (ValueError, OSError):
                pass

    def _bucket(self):
        month = dt.datetime.utcnow().strftime("%Y-%m")
        node = self._state.setdefault(self.name, {})
        if node.get("month") != month:
            node.clear()
            node["month"] = month
            node["symbols"] = []
        return node

    def used(self):
        return set(self._bucket().get("symbols", []))

    def remaining(self):
        return max(0, self.limit - len(self.used()))

    def would_cost(self, symbols):
        """How many NEW symbols a batch would consume (already-seen ones are free)."""
        return len(set(s.upper() for s in symbols) - self.used())

    def claim(self, symbol):
        """Record a symbol. Returns False if it would exceed the monthly cap."""
        node = self._bucket()
        seen = set(node["symbols"])
        s = symbol.upper()
        if s in seen:
            return True
        if len(seen) >= self.limit:
            return False
        node["symbols"].append(s)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._state, f)
        os.replace(tmp, self.state_path)
        return True


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
