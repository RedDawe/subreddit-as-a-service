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
GATE_TICKERS = {
    "SIVB": "bank failure, Mar 2023",
    "BBBYQ": "bankruptcy, Apr 2023",
    "ATVI": "acquired by Microsoft at a premium, Oct 2023",
    "FRCB": "bank failure, May 2023",
    "TWTR": "taken private, Oct 2022",
}
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


ADAPTERS = {"yfinance": YFinance, "sharadar": Sharadar}


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

    missing = []
    for t, why in GATE_TICKERS.items():
        try:
            rows = adapter.history(t, *GATE_WINDOW)
        except Exception as e:                       # noqa: BLE001
            rows = []
            report[f"{t}_error"] = str(e)[:120]
        report[t] = len(rows)
        if len(rows) < 100:
            missing.append((t, why))

    if verbose:
        print(f"adapter        : {adapter.name}")
        print(f"claims delisting returns: {adapter.has_delisting_returns}")
        for t, n in report.items():
            print(f"  {t:12} {n} rows")

    if missing:
        if verbose:
            print("\nFAIL - no data for names that stopped trading:")
            for t, why in missing:
                print(f"  {t:6} ({why})")
            print("\nUsing this source would silently drop these names from the")
            print("universe. Both tails are affected: bankruptcies AND acquisitions.")
            print("Supply a delisting-inclusive source (4.4) before computing returns.")
        return False, report

    if verbose:
        print("\nPASS - delisted names are present and priced.")
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
