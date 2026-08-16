"""Fama-French 5 factors + momentum, from the Ken French data library (free).

Design doc 3.3 is emphatic: measured against SPY over 2015-2025 a portfolio of
value names will look bad largely because the value factor looked bad, and that
is a fact about the factor rather than about the subreddit. Factor-adjusted
alpha is the only interpretable version of the portfolio test.

The library ships monthly CSVs in a fixed-width-ish format with header preamble,
an annual section appended after the monthly one, and percent units. All three
are handled here; the annual section in particular will silently corrupt a naive
parse, because its 4-digit "dates" look like early monthly dates.

No key, no rate limit - just a static ZIP.
"""

import io
import os
import urllib.request
import zipfile

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FF5 = "F-F_Research_Data_5_Factors_2x3_CSV.zip"
MOM = "F-F_Momentum_Factor_CSV.zip"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "factors")


def _download(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name.replace(".zip", ".csv"))
    if os.path.exists(path):
        return path
    with urllib.request.urlopen(BASE + name, timeout=180) as r:
        blob = r.read()
    z = zipfile.ZipFile(io.BytesIO(blob))
    inner = z.namelist()[0]
    with open(path, "wb") as f:
        f.write(z.read(inner))
    return path


def _parse(path):
    """Return {YYYY-MM: {factor: decimal_return}} for the monthly section only."""
    rows = {}
    header = None
    with open(path, encoding="latin-1") as f:
        for raw in f:
            parts = [p.strip() for p in raw.rstrip("\n").split(",")]
            key = parts[0] if parts else ""

            # The header is the line whose FIRST field is empty and which has
            # named columns after it. It must be tested before any blank-line
            # skip, or it gets swallowed along with the preamble.
            if header is None:
                if len(parts) > 1 and key == "" and any(parts[1:]):
                    header = [p for p in parts[1:] if p]
                continue

            if key.isdigit() and len(key) == 6:              # YYYYMM
                try:
                    vals = [float(v) / 100.0 for v in parts[1:len(header) + 1]]
                except ValueError:
                    continue
                rows[f"{key[:4]}-{key[4:]}"] = dict(zip(header, vals))
            elif rows:
                # Once monthly data has started, anything that is not YYYYMM
                # means the annual section (4-digit "dates", which would parse
                # as year 0196 and silently corrupt the table). Stop.
                break
    return rows


def load():
    """Merged monthly factor table: Mkt-RF, SMB, HML, RMW, CMA, RF, Mom."""
    ff = _parse(_download(FF5))
    try:
        mom = _parse(_download(MOM))
    except Exception:                                        # noqa: BLE001
        mom = {}
    for k, v in ff.items():
        m = mom.get(k, {})
        for name in ("Mom", "Mom   ", "MOM"):
            if name in m:
                v["Mom"] = m[name]
                break
    return ff


def ols(y, X):
    """Least squares with an intercept, via normal equations. Returns (alpha, betas)."""
    n = len(y)
    k = len(X[0])
    A = [[1.0] + list(row) for row in X]
    XtX = [[sum(A[i][a] * A[i][b] for i in range(n)) for b in range(k + 1)]
           for a in range(k + 1)]
    Xty = [sum(A[i][a] * y[i] for i in range(n)) for a in range(k + 1)]
    # Gaussian elimination with partial pivoting
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    size = k + 1
    for c in range(size):
        piv = max(range(c, size), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None, None
        M[c], M[piv] = M[piv], M[c]
        for r in range(size):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for cc in range(c, size + 1):
                M[r][cc] -= f * M[c][cc]
    sol = [M[i][size] / M[i][i] for i in range(size)]
    return sol[0], sol[1:]


if __name__ == "__main__":
    f = load()
    ks = sorted(f)
    print(f"months: {len(ks)}  {ks[0]} .. {ks[-1]}")
    print("factors:", sorted(f[ks[-1]].keys()))
    for k in ks[-3:]:
        print(" ", k, {a: round(b, 4) for a, b in f[k].items()})
