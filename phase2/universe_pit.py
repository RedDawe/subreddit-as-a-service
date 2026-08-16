"""Point-in-time listing universe, from Tiingo's free `supported_tickers` file.

Design doc §4.4 requires point-in-time universe membership and §3.2 needs, for
every (ticker, month) mention, a pool of *unmentioned* stocks that were actually
listed in that month to draw matched controls from. Using today's listed universe
for a 2019 control pool is the "point-in-time universe violation" in the bias
register (§8), and it flatters the sub.

Tiingo publishes ticker, exchange, assetType, startDate and endDate for ~108k
symbols as a static ZIP - no API call, no rate limit, no symbol quota. 16.4k of
those are US-exchange stocks and 7.2k of those stopped reporting before 2025, so
the dead names are present rather than silently absent.

Two traps this module encodes, both found by inspection:

  1. `endDate` is the LAST OBSERVATION DATE, not a delisting date. Names still
     trading carry an endDate of roughly today. So "delisted" means the series
     terminated well before the file's own max date, not merely "has an endDate"
     - every row has one.

  2. The master list carries the FINAL ticker, while price history answers to the
     ticker in use at the time. Silicon Valley Bank appears only as `SIVBQ` (the
     post-bankruptcy PINK symbol); its prices are served under `SIVB`, which is
     absent from the list entirely. Membership lookups must therefore tolerate a
     miss rather than treat absence as "was never listed".
"""

import csv
import datetime as dt
import io
import os
import urllib.request
import zipfile

URL = "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "tiingo_tickers.csv")

US_EXCHANGES = {"NYSE", "NASDAQ", "NYSE MKT", "AMEX", "NYSE ARCA", "BATS"}
# Bankruptcy/liquidation suffixes: a name that moved to PINK under one of these
# has effectively stopped being an exchange-listed company.
DISTRESS_SUFFIXES = ("Q", "QB")


def download(force=False):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    if os.path.exists(CACHE) and not force:
        return CACHE
    with urllib.request.urlopen(URL, timeout=180) as r:
        blob = r.read()
    z = zipfile.ZipFile(io.BytesIO(blob))
    name = z.namelist()[0]
    with open(CACHE, "wb") as out:
        out.write(z.read(name))
    return CACHE


class PitUniverse:
    def __init__(self, path=None, us_only=True, stocks_only=True):
        path = path or download()
        self.rows = []
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                if stocks_only and r["assetType"] != "Stock":
                    continue
                if us_only and r["exchange"] not in US_EXCHANGES:
                    continue
                if not r["startDate"] or not r["endDate"]:
                    continue
                self.rows.append(r)
        self.by_ticker = {}
        for r in self.rows:
            self.by_ticker.setdefault(r["ticker"], []).append(r)
        # The file's own maximum endDate is "as of" - names still trading carry
        # it. Anything ending materially earlier actually stopped.
        self.as_of = max(r["endDate"] for r in self.rows) if self.rows else ""

    # ------------------------------------------------------------------ api

    def was_listed(self, ticker, date):
        """True if `ticker` was listed on `date` (ISO string). None if unknown."""
        recs = self.by_ticker.get(ticker.upper())
        if not recs:
            return None                      # absent != delisted (see trap 2)
        return any(r["startDate"] <= date <= r["endDate"] for r in recs)

    def last_observed(self, ticker):
        recs = self.by_ticker.get(ticker.upper())
        return max((r["endDate"] for r in recs), default=None) if recs else None

    def is_dead(self, ticker, grace_days=30):
        """True if the series terminated meaningfully before the file's as-of date."""
        last = self.last_observed(ticker)
        if not last:
            return None
        cutoff = (dt.date.fromisoformat(self.as_of)
                  - dt.timedelta(days=grace_days)).isoformat()
        return last < cutoff

    def universe_at(self, date):
        """Tickers listed on `date` - the control pool for §3.2 matching."""
        return {r["ticker"] for r in self.rows
                if r["startDate"] <= date <= r["endDate"]}

    def summary(self):
        dead = sum(1 for t in self.by_ticker if self.is_dead(t))
        return {"rows": len(self.rows), "tickers": len(self.by_ticker),
                "as_of": self.as_of, "terminated_before_as_of": dead}


if __name__ == "__main__":
    u = PitUniverse()
    print(u.summary())
    for d in ("2015-06-30", "2019-06-28", "2021-06-30", "2023-06-30", "2026-06-30"):
        print(f"  US-listed stocks on {d}: {len(u.universe_at(d)):,}")
    print()
    for t in ("AAPL", "ATVI", "TWTR", "BBBYQ", "SIVB", "SIVBQ"):
        print(f"  {t:7} last_observed={u.last_observed(t)} dead={u.is_dead(t)} "
              f"listed_2021-06-30={u.was_listed(t, '2021-06-30')}")
