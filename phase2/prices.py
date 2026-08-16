"""Price data adapters + the design doc 7 Phase 2 gate.

Design doc 4.4: "This choice determines whether the answer is true." Free
sources silently drop delisted tickers, so a backtest that cannot price the
bankruptcies will look excellent and be fiction.

Measured in this environment (phase0/FEASIBILITY.md, Finding 4), yfinance
returns 1258 rows for AAPL over 2019-2024 and zero rows for SIVB, BBBYQ and
ATVI. ATVI is the instructive one: it was *acquired at a premium*, not
bankrupted, and it still vanishes. So the damage is two-sided - the survivors
file drops a class of winners as well as the wipeouts - which is worse than the
one-directional bias the bias register anticipates.

Hence the design here: every adapter must pass `gate()` before it may be used
for returns. An adapter that cannot price known-dead tickers raises rather than
quietly producing a beautiful, wrong answer.

Adding a paid source: implement Adapter.history() and register it. Nothing else
in the pipeline changes.
"""

import os

# Known outcomes during the study period, chosen to span the failure modes that
# matter: bankruptcy, bank failure, and acquisition. An adapter that handles
# bankruptcies but not acquisitions still corrupts the winner tail.
#   ticker: (description, expected last trade date or None if it kept trading OTC)
#
# The expected end date matters as much as the row count. A source that
# forward-fills a delisted name with a stale price passes a "does it return
# rows" check while producing fiction, so the gate also asks whether the series
# STOPS when the company did.
GATE_TICKERS = {
    "SIVB": ("bank failure, Mar 2023 (kept trading OTC)", None),
    "BBBYQ": ("bankruptcy, Apr 2023", "2023-09-29"),
    "ATVI": ("acquired by Microsoft at a premium, Oct 2023", "2023-10-13"),
    "FRCB": ("bank failure, May 2023 (kept trading OTC)", None),
    "TWTR": ("taken private, Oct 2022", "2022-10-28"),
}
END_DATE_TOLERANCE_DAYS = 20
GATE_CONTROL = "AAPL"
GATE_WINDOW = ("2019-01-01", "2024-01-01")


class PriceUnavailable(Exception):
    pass


class Adapter:
    name = "abstract"
    has_delisting_returns = False

    def history(self, ticker, start, end):
        """Return a list of (date, total_return_adjusted_close). May be empty."""
        raise NotImplementedError


class YFinance(Adapter):
    """Free source. Retained for development only - see gate()."""

    name = "yfinance"
    has_delisting_returns = False

    def __init__(self):
        os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
        os.environ.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")

    def history(self, ticker, start, end):
        import warnings
        warnings.filterwarnings("ignore")
        import requests
        import yfinance as yf
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0"
        df = yf.Ticker(ticker, session=s).history(start=start, end=end, auto_adjust=True)
        return [(i.date().isoformat(), float(r["Close"])) for i, r in df.iterrows()]


class Sharadar(Adapter):
    """Nasdaq Data Link / Sharadar SEP + TICKERS. Needs NASDAQ_DATA_LINK_API_KEY.

    SEP carries dividend- and split-adjusted closes and, critically, retains
    delisted tickers, which is what the gate is checking for.
    """

    name = "sharadar"
    has_delisting_returns = True

    def __init__(self, key=None):
        self.key = key or os.environ.get("NASDAQ_DATA_LINK_API_KEY")
        if not self.key:
            raise PriceUnavailable("NASDAQ_DATA_LINK_API_KEY is not set")

    def history(self, ticker, start, end):
        import json
        import urllib.parse
        import urllib.request
        q = urllib.parse.urlencode({
            "ticker": ticker, "date.gte": start, "date.lt": end,
            "qopts.columns": "date,closeadj", "api_key": self.key,
        })
        url = f"https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP.json?{q}"
        with urllib.request.urlopen(url, timeout=90) as r:
            payload = json.loads(r.read())
        rows = payload["datatable"]["data"]
        return [(d, float(c)) for d, c in rows if c is not None]


class Tiingo(Adapter):
    """Tiingo EOD composite prices. Free tier, key in TIINGO_API_KEY.

    Free-tier limits (vendor pricing page, 2026-08): 50 req/hour, 1000 req/day,
    1 GB/month, and **500 unique symbols per month**. The symbol cap is the
    binding one for this study and is tracked persistently across runs, so a
    re-run cannot silently burn the month's quota.

    `adjClose` is dividend- and split-adjusted, which is what design doc 4.4
    means by total return. History goes back 30+ years, so unlike the free
    Massive tier this actually reaches the study's formation cohorts.
    """

    name = "tiingo"
    has_delisting_returns = True      # measured by gate(): all 5 dead names priced,
                                      # each series terminating on its real last trade date

    def __init__(self, key=None):
        self.key = key or os.environ.get("TIINGO_API_KEY")
        if not self.key:
            raise PriceUnavailable("TIINGO_API_KEY is not set")
        from ratelimit import tiingo_limiter, tiingo_symbol_budget
        self.limiter = tiingo_limiter()
        self.budget = tiingo_symbol_budget()

    def history(self, ticker, start, end):
        import json
        import urllib.error
        import urllib.request
        # Wait FIRST, then claim. Claiming before the wait spends a symbol from
        # the monthly budget and then blocks for up to an hour; if the process
        # is killed while waiting, that symbol is burned with nothing fetched.
        self.limiter.wait()
        if not self.budget.claim(ticker):
            raise PriceUnavailable(
                f"monthly unique-symbol cap reached ({self.budget.limit}); "
                f"{ticker} not fetched. Resets on the 1st."
            )
        url = (f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
               f"?startDate={start}&endDate={end}&token={self.key}")
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                rows = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []                     # unknown/uncovered symbol
            if e.code == 429:
                raise PriceUnavailable(f"tiingo rate limited: {e.read()[:200]!r}") from e
            raise
        return [(row["date"][:10], float(row["adjClose"])) for row in rows
                if row.get("adjClose") is not None]

    def history_full(self, ticker, start, end):
        """Same call, but keeping volume - used as a free size/liquidity proxy.

        Tiingo's free tier exposes no market cap or sector, so dollar volume
        (close x volume) stands in as the size variable for the matched-lift
        adjustment. It is a well-understood size/liquidity proxy and costs
        nothing extra, since it rides on a request we are making anyway.
        """
        import json
        import urllib.error
        import urllib.request
        # Wait FIRST, then claim. Claiming before the wait spends a symbol from
        # the monthly budget and then blocks for up to an hour; if the process
        # is killed while waiting, that symbol is burned with nothing fetched.
        self.limiter.wait()
        if not self.budget.claim(ticker):
            raise PriceUnavailable(
                f"monthly unique-symbol cap reached ({self.budget.limit}); "
                f"{ticker} not fetched. Resets on the 1st."
            )
        url = (f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
               f"?startDate={start}&endDate={end}&token={self.key}")
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                rows = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            if e.code == 429:
                raise PriceUnavailable(f"tiingo rate limited: {e.read()[:200]!r}") from e
            raise
        return [{"date": r["date"][:10], "adj_close": r.get("adjClose"),
                 "close": r.get("close"), "volume": r.get("volume")}
                for r in rows if r.get("adjClose") is not None]


class Massive(Adapter):
    """Massive (formerly Polygon.io) aggregates. Free "Basic" plan.

    Kept for completeness and rejected by `gate()` in practice: the free tier
    serves only a rolling ~2-year window (a 2019 request returns NOT_AUTHORIZED
    "your plan doesn't include this data timeframe", and so does 2024-01 as of
    2026-08). That cannot reach this study's formation cohorts, let alone their
    5-year forward windows.
    """

    name = "massive"
    has_delisting_returns = False
    FREE_TIER_YEARS = 2

    def __init__(self, key=None):
        self.key = key or os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
        if not self.key:
            raise PriceUnavailable("MASSIVE_API_KEY / POLYGON_API_KEY is not set")
        from ratelimit import massive_limiter
        self.limiter = massive_limiter()

    def history(self, ticker, start, end):
        import json
        import urllib.error
        import urllib.request
        self.limiter.wait()
        url = (f"https://api.massive.com/v2/aggs/ticker/{ticker}/range/1/day/"
               f"{start}/{end}?adjusted=true&limit=50000&apiKey={self.key}")
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                payload = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PriceUnavailable(
                    f"massive rejected the request ({e.code}); the free tier serves "
                    f"only ~{self.FREE_TIER_YEARS} years of history"
                ) from e
            if e.code == 429:
                raise PriceUnavailable("massive rate limited (5 req/min on free)") from e
            raise
        if payload.get("status") == "NOT_AUTHORIZED":
            raise PriceUnavailable(f"massive: {payload.get('message', '')[:160]}")
        import datetime as _dt
        return [(_dt.datetime.utcfromtimestamp(r["t"] / 1000).date().isoformat(),
                 float(r["c"])) for r in payload.get("results", [])]


ADAPTERS = {"yfinance": YFinance, "sharadar": Sharadar,
            "tiingo": Tiingo, "massive": Massive}


def gate(adapter, verbose=True):
    """Phase 2 gate: can this source price names that stopped trading?

    Returns (passed, report). Refuses on any gate ticker returning no data.
    """
    report = {}
    control = adapter.history(GATE_CONTROL, *GATE_WINDOW)
    report[GATE_CONTROL] = len(control)
    if len(control) < 500:
        return False, {"error": f"control {GATE_CONTROL} returned {len(control)} rows; "
                                "the adapter is broken, not merely incomplete"}

    import datetime as _dt

    missing, stale = [], []
    detail = {}
    for t, (why, expect_end) in GATE_TICKERS.items():
        try:
            rows = adapter.history(t, *GATE_WINDOW)
        except Exception as e:                       # noqa: BLE001
            rows = []
            report[f"{t}_error"] = str(e)[:120]
        report[t] = len(rows)
        last = rows[-1][0] if rows else None
        detail[t] = (len(rows), last, rows[-1][1] if rows else None)
        if len(rows) < 100:
            missing.append((t, why))
        elif expect_end and last:
            drift = abs((_dt.date.fromisoformat(last)
                         - _dt.date.fromisoformat(expect_end)).days)
            if drift > END_DATE_TOLERANCE_DAYS:
                stale.append((t, why, last, expect_end))

    if verbose:
        print(f"adapter        : {adapter.name}")
        print(f"claims delisting returns: {adapter.has_delisting_returns}")
        print(f"  {'ticker':8}{'rows':>7}  {'last trade':12}{'last close':>11}")
        for t, (n, last, px) in detail.items():
            print(f"  {t:8}{n:>7}  {str(last):12}"
                  f"{('%.2f' % px) if px is not None else '-':>11}")

    if missing or stale:
        if verbose:
            for t, why in missing:
                print(f"\nFAIL {t}: no data ({why})")
            for t, why, last, exp in stale:
                print(f"\nFAIL {t}: series runs to {last} but trading ended {exp} "
                      f"({why}).\n  The source is padding a dead name with stale "
                      "prices, which is worse than\n  omitting it - the backtest "
                      "would show a flat hold instead of the real outcome.")
            print("\nRefusing this source for returns (4.4).")
        return False, report

    if verbose:
        print("\nPASS - delisted names are present, priced, and each series ends")
        print("  when the company actually stopped trading (no forward-filling).")
    return True, report


def get(name=None, enforce=True):
    """Return a gated adapter. Raises unless the source can price dead tickers."""
    name = name or os.environ.get("PRICE_SOURCE", "sharadar")
    if name not in ADAPTERS:
        raise PriceUnavailable(f"unknown adapter {name!r}; have {sorted(ADAPTERS)}")
    adapter = ADAPTERS[name]()
    if enforce:
        ok, report = gate(adapter, verbose=False)
        if not ok:
            raise PriceUnavailable(
                f"adapter {name!r} failed the delisting gate: {report}. "
                "Refusing to compute returns from a survivors-only universe (4.4)."
            )
    return adapter


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "yfinance"
    try:
        a = ADAPTERS[which]()
    except PriceUnavailable as e:
        print(f"{which}: unavailable - {e}")
        sys.exit(2)
    ok, _ = gate(a)
    sys.exit(0 if ok else 1)
