"""S&P 500 membership and GICS sector, scraped from Wikipedia (free).

Design doc §1.3 asks what share of mentions sit outside the S&P 500 and outside
the top 1,000 by market cap — the novelty hypothesis, and the one the doc
expects to fail. §3.2 also wants GICS sector for matching; SIC (phase2/sectors.py)
was a stand-in because GICS is not freely licensed, but Wikipedia's constituent
table carries the GICS sector and sub-industry for current members.

**Known limitation, and it runs one way.** This is *current* membership plus a
"date added" column. A company that was in the index in 2021 and has since been
removed does not appear at all, so historical membership is UNDERCOUNTED. Names
wrongly classified as "outside the S&P 500" therefore inflate the measured
novelty — the bias flatters the subreddit on exactly the hypothesis §1.3 says is
most likely to fail. A5 must state this rather than report novelty as a clean
number.

`date_added` does let membership be excluded correctly in one direction: a name
added in 2023 was definitely not a member in 2021.
"""

import os
import re
import urllib.request

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = os.environ.get("SEC_UA", "subreddit-screener-study contact@example.com")
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "sp500.csv")

_TAG = re.compile(r"<[^>]+>")


def _clean(x):
    return _TAG.sub("", x).replace("&amp;", "&").strip()


def fetch(force=False):
    """ticker -> {"name", "gics_sector", "gics_sub", "date_added"}."""
    if os.path.exists(CACHE) and not force:
        import csv
        with open(CACHE, newline="") as f:
            return {r["ticker"]: r for r in csv.DictReader(f)}

    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        html = r.read().decode("utf-8", "ignore")

    tables = re.findall(
        r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.S)
    if not tables:
        raise RuntimeError("constituent table not found")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[0], re.S)
    out = {}
    for row in rows[1:]:
        c = [_clean(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(c) < 6 or not c[0]:
            continue
        # Wikipedia writes class shares with a dot; price data uses a dash.
        ticker = c[0].replace(".", "-").upper()
        out[ticker] = {"ticker": ticker, "name": c[1], "gics_sector": c[2],
                       "gics_sub": c[3], "date_added": c[5]}

    import csv
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name", "gics_sector",
                                          "gics_sub", "date_added"])
        w.writeheader()
        w.writerows(out.values())
    return out


def in_index_at(members, ticker, date):
    """Membership on `date`, as far as a current snapshot can tell.

    Returns True / False / None:
        True  - currently a member and added on or before `date`
        None  - currently a member but added after `date`, OR not currently a
                member at all. The second case is genuinely unknown: the name
                may have been a member and been removed since.
    """
    m = members.get(ticker.upper())
    if not m:
        return None                      # unknown, NOT a confident "outside"
    added = (m.get("date_added") or "")[:10]
    if added and added <= date:
        return True
    return None if not added else False


if __name__ == "__main__":
    import collections
    m = fetch()
    print(f"current S&P 500 constituents: {len(m)}")
    print("GICS sectors:",
          collections.Counter(v["gics_sector"] for v in m.values()).most_common(5))
    for t in ("AAPL", "NVDA", "GOOGL", "BRK-B"):
        print(f"  {t:6} in index at 2021-06-30 -> {in_index_at(m, t, '2021-06-30')}")
