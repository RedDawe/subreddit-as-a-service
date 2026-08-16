"""SIC sector codes from SEC's Financial Statement Data Sets (free, bulk).

Design doc §3.2 wants matched controls on market-cap decile, GICS sector and
listing country. The bias register listed sector as uncontrolled "no free
source" — that was wrong. SEC publishes quarterly datasets whose `sub.txt`
carries `cik`, `name`, `sic` and `countryba` for every filer in the quarter, as
a single ~100 MB ZIP with no key and no rate limit.

What this module does NOT do is add sector to the lift estimator. With ~220
controls, crossing 5 size strata with ~10 sector divisions gives 50 cells and
roughly 4 controls each, which would produce noise rather than adjustment. So
sector is used as a DIAGNOSTIC: it measures how far the subreddit's sector mix
departs from the universe, which is a real finding about what the sub is, and
it makes the residual confound explicit instead of merely asserted.

SIC is mapped to the standard SEC divisions rather than GICS, which is not
freely available.
"""

import csv
import io
import os
import urllib.request
import zipfile

BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/"
UA = os.environ.get("SEC_UA", "subreddit-screener-study contact@example.com")
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "sic_map.csv")

# SEC SIC divisions (the coarse grouping the agency itself uses).
DIVISIONS = [
    ((100, 999), "agriculture"), ((1000, 1499), "mining"),
    ((1500, 1799), "construction"), ((2000, 3999), "manufacturing"),
    ((4000, 4999), "transport_utilities"), ((5000, 5199), "wholesale"),
    ((5200, 5999), "retail"), ((6000, 6799), "finance_insurance_re"),
    ((7000, 8999), "services"), ((9100, 9999), "public_admin"),
]


def division(sic):
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "unknown"
    for (lo, hi), name in DIVISIONS:
        if lo <= s <= hi:
            return name
    return "unknown"


def build(quarters=("2020q2",), force=False):
    """cik -> (sic, division, country). Cached to CSV after the first build."""
    if os.path.exists(CACHE) and not force:
        out = {}
        with open(CACHE, newline="") as f:
            for r in csv.DictReader(f):
                out[int(r["cik"])] = (r["sic"], r["division"], r["country"])
        return out

    merged = {}
    for q in quarters:
        req = urllib.request.Request(BASE + f"{q}.zip", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            blob = r.read()
        z = zipfile.ZipFile(io.BytesIO(blob))
        with z.open("sub.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"),
                                      delimiter="\t"):
                try:
                    cik = int(row["cik"])
                except (TypeError, ValueError):
                    continue
                sic = (row.get("sic") or "").strip()
                if sic:
                    merged[cik] = (sic, division(sic),
                                   (row.get("countryba") or "").strip())

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cik", "sic", "division", "country"])
        for cik, (sic, div, ctry) in sorted(merged.items()):
            w.writerow([cik, sic, div, ctry])
    return merged


if __name__ == "__main__":
    import collections
    m = build()
    print(f"CIKs with a SIC code: {len(m):,}")
    print("division mix:",
          collections.Counter(v[1] for v in m.values()).most_common(6))
