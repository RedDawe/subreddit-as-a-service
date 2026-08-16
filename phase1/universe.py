"""Ticker universe + company-name aliases, built from SEC EDGAR.

Serves design doc 4.4's requirement that mentions resolve to a stable entity ID
(here: CIK) rather than to a ticker string.

Important limitation, carried through to the writeup: EDGAR's company_tickers
files are a *current-state* snapshot. They do not give point-in-time membership,
so a ticker that was reassigned between the mention date and today will resolve
to today's owner. Quantified in phase1/QUALITY.md; must be fixed with EDGAR
former-names data before any return is computed off this map.
"""

import json
import os
import re
import urllib.request

UA = os.environ.get("SEC_UA", "subreddit-screener-study contact@example.com")
SEC_EXCHANGE = "https://www.sec.gov/files/company_tickers_exchange.json"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "sec_universe.json")

# Corporate suffixes stripped when deriving a searchable company alias.
SUFFIXES = re.compile(
    r"\b(corp|corporation|inc|incorporated|co|company|ltd|limited|plc|holdings?|"
    r"group|the|sa|nv|ag|llc|lp|trust|reit|class [abc]|adr|new|com)\b\.?",
    re.I,
)


def load_sec(force=False):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    if os.path.exists(CACHE) and not force:
        return json.load(open(CACHE))
    req = urllib.request.Request(SEC_EXCHANGE, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = json.loads(r.read())
    fields = raw["fields"]
    rows = [dict(zip(fields, rec)) for rec in raw["data"]]
    json.dump(rows, open(CACHE, "w"))
    return rows


def normalise_name(name):
    n = name.lower()
    n = re.sub(r"[^a-z0-9 &]", " ", n)
    n = SUFFIXES.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


# Investors, authors and schools of thought whose surnames are also listed
# companies. In a value-investing sub these appear constantly as people, so the
# company reading is the rare one and is not worth the false positives.
# "Graham" alone accounted for 13 spurious Graham Holdings mentions.
PERSON_NAMES = {
    "graham", "buffett", "munger", "dodd", "lynch", "fisher", "greenblatt",
    "klarman", "pabrai", "marks", "templeton", "schloss", "burry", "ackman",
    "icahn", "soros", "dalio", "bogle", "shiller", "damodaran", "greenwald",
}

# Frequency rank below which a single word is too common to be a safe alias.
ALIAS_DISTINCTIVE_RANK = 50_000


def _distinctive(word):
    """True when `word` is rare enough in English to stand alone as a company alias."""
    if word in PERSON_NAMES:
        return False
    try:
        from wordfreq import zipf_frequency
    except ImportError:                                   # pragma: no cover
        return len(word) >= 6
    # Zipf 3.0 is roughly "appears once per million words" - below that a word
    # is rare enough that a capitalised occurrence is plausibly a company.
    return zipf_frequency(word, "en") < 3.0


def _tiingo_delisted_tickers():
    """US-listed tickers from Tiingo's file, INCLUDING ones that have died.

    SEC's company_tickers file is current-state, so a company that was acquired
    or delisted simply is not in it. Foot Locker (FL) was acquired in 2025 and
    is absent, which means the extractor could not recognise "$FL" in a 2022
    post at all. That is survivorship bias inside the EXTRACTION stage - the
    mention set silently loses exactly the acquired and bankrupt names whose
    outcomes the study most needs - and it is a different bug from the
    survivorship in price data that 4.4 warns about.

    Tiingo's static ticker file carries start/end dates for ~7.4k terminated US
    listings, so it is used to top up the ticker vocabulary. These entries have
    no CIK, so they get a synthetic entity id and are flagged.
    """
    import csv
    path = os.path.join(os.path.dirname(__file__), "..", "data", "tiingo_tickers.csv")
    if not os.path.exists(path):
        return {}
    us = {"NYSE", "NASDAQ", "NYSE MKT", "AMEX", "NYSE ARCA", "BATS"}
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("assetType") != "Stock" or r.get("exchange") not in us:
                continue
            t = (r.get("ticker") or "").upper().strip()
            if t:
                out.setdefault(t, {"start": r.get("startDate"), "end": r.get("endDate")})
    return out


def build():
    """Return (by_ticker, name_aliases).

    by_ticker    : TICKER -> {cik, name, exchange}
    name_aliases : normalised company name -> cik  (only names distinctive
                   enough to be worth matching on)
    """
    rows = load_sec()
    by_ticker, name_aliases = {}, {}

    for r in rows:
        tic = (r.get("ticker") or "").upper().strip()
        cik = r.get("cik")
        if not tic or not cik:
            continue
        # First listing wins; EDGAR orders roughly by prominence, so this
        # prefers the common share class over odd secondary lines.
        by_ticker.setdefault(tic, {"cik": cik, "name": r["name"], "exchange": r.get("exchange")})

        alias = normalise_name(r["name"])
        # One-word aliases shorter than 4 chars are noise ("box", "ari").
        if len(alias) >= 4 and " " not in alias:
            if _distinctive(alias):
                name_aliases.setdefault(alias, cik)
        elif " " in alias and len(alias) >= 6:
            name_aliases.setdefault(alias, cik)
            head = alias.split()[0]
            # "berkshire hathaway" should also fire on "berkshire". But the head
            # word of a stripped name is very often a generic noun - Capital One
            # -> "capital", United Rentals -> "united", Graham Holdings ->
            # "graham" - and those match ordinary prose constantly. Length is not
            # a sufficient filter (all of those are >= 6 chars), so the head must
            # be distinctive, not merely long.
            if len(head) >= 6 and _distinctive(head):
                name_aliases.setdefault(head, cik)

    # Top up with tickers that existed historically but are gone from EDGAR's
    # current-state file. SEC entries always win, so live names keep their CIK.
    for t, meta in _tiingo_delisted_tickers().items():
        if t not in by_ticker:
            by_ticker[t] = {"cik": f"TIINGO:{t}", "name": t,
                            "exchange": None, "delisted": True,
                            "listed_from": meta["start"], "listed_to": meta["end"]}

    return by_ticker, name_aliases


# Hand-curated aliases for names the sub uses constantly in forms EDGAR
# does not carry. Kept small and explicit rather than fuzzy-matched.
MANUAL_ALIASES = {
    "berkshire": 1067983, "brk": 1067983, "brk a": 1067983, "brk b": 1067983,
    "google": 1652044, "alphabet": 1652044,
    "facebook": 1326801, "meta": 1326801,
    "apple": 320193, "microsoft": 789019, "amazon": 1018724,
    "tesla": 1318605, "nvidia": 1045810, "netflix": 1065280,
    "intel": 50863, "disney": 1744489, "walmart": 104169,
    "coca cola": 21344, "coke": 21344, "pepsi": 77476,
    "jpmorgan": 19617, "jp morgan": 19617, "goldman": 886982,
    "exxon": 34088, "chevron": 93410, "pfizer": 78003,
    "verizon": 732712, "at t": 732717, "boeing": 12927,
    "target": 27419, "costco": 909832, "nike": 320187,
    "starbucks": 829224, "mcdonalds": 63908, "salesforce": 1108524,
    "paypal": 1633917, "adobe": 796343, "oracle": 1341439,
    "qualcomm": 804328, "broadcom": 1730168, "cisco": 858877,
    # Abbreviations the sub uses constantly that EDGAR's legal names never carry.
    "j&j": 200406, "jnj": 200406, "johnson & johnson": 200406,
    "p&g": 80424, "procter & gamble": 80424,
    "ge": 40545, "3m": 66740, "amd": 2488, "ibm": 51143,
}


if __name__ == "__main__":
    bt, na = build()
    na.update(MANUAL_ALIASES)
    print(f"tickers: {len(bt)}   name aliases: {len(na)}")
    for t in ("AAPL", "BRK-B", "KEY", "ALL", "ON"):
        print(f"  {t:6} -> {bt.get(t)}")
