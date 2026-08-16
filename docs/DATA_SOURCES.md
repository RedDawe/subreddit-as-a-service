# Data sources, limits, and what each one can actually do

Everything here was measured from this container, not taken from marketing pages.
No credentials appear in this repo — they live in a gitignored `.env` and are read
from the environment.

## Summary

| Source | Cost | Verdict for this study |
|---|---|---|
| Arctic Shift | free | **primary** Reddit source, 2010-09 → present |
| Tiingo | free tier | **primary** price source — passes the delisting gate |
| Tiingo `supported_tickers` | free, static file | **point-in-time universe** (§4.4, §3.2) |
| SEC EDGAR | free | ticker → CIK entity map |
| Massive (ex-Polygon) | free tier | **unusable** — rolling ~2-year history |
| yfinance | free | **rejected** by the gate — see below |

## Tiingo — the blocker is resolved, on the free tier

§4.4 called delisting-inclusive pricing the choice that "determines whether the
answer is true", and assumed it had to be bought. It does not.

Gate results (2019-01-01 → 2024-01-01):

    ticker     rows  last trade   last close
    AAPL       1258  2023-12-29       190.21
    SIVB       1258  2023-12-29         0.03
    BBBYQ      1195  2023-09-29         0.08
    ATVI       1205  2023-10-13        94.42
    FRCB       1258  2023-12-29         0.04
    TWTR        965  2022-10-28        53.70

The row counts alone would not be convincing — a source that forward-fills a
dead name with a stale price also "returns rows". What makes this trustworthy is
that **each series stops when the company did**:

- `ATVI` ends 2023-10-13 at $94.42 — the Microsoft acquisition close.
- `TWTR` ends 2022-10-28 at $53.70 — the take-private, at roughly the deal price.
- `BBBYQ` ends 2023-09-29 at $0.08 — the real end of the bankruptcy stub.
- `SIVB` runs to $0.03, correctly capturing a 195 → 0.03 wipeout rather than
  omitting it.

The gate in `phase2/prices.py` now checks end dates against known event dates
with a 20-day tolerance, so forward-filling would fail it.

`adjClose` is dividend- and split-adjusted, which is §4.4's total-return
requirement. History goes back 30+ years.

### Free-tier limits (enforced in `phase2/ratelimit.py`)

    50 requests / hour
    1,000 requests / day
    1 GB / month bandwidth
    500 UNIQUE SYMBOLS / month   <- the binding constraint

The symbol cap is what shapes the work. The corpus has 4,316 distinct mentioned
entities; the usable-cohort funnel is ~721–810 names per year. **A full pass
therefore spans multiple months**, and symbols must be spent deliberately.
`SymbolBudget` tracks them persistently on disk so a re-run cannot silently burn
the month's quota, and `remaining()` is meant to be consulted before planning a
batch.

Suggested spending order, cheapest question first:

1. The ≥3-distinct-author names for one cohort year (~233 symbols in 2021) —
   the strongest signal, and it fits inside a single month's quota.
2. Their matched controls (§3.2 needs k=5 per mention — this is the expensive
   part and should be sampled, not exhaustive).
3. Widen to ≥2× names only if the first pass shows something.

## Tiingo `supported_tickers` — a free point-in-time universe

A static ZIP, so no API call and no quota: 108,327 symbols with `startDate` and
`endDate`. Filtered to US-exchange common stocks: **16,422 tickers, of which
7,378 stopped reporting before the file's as-of date.**

This directly serves two things the design doc flags as hard:

- §4.4's point-in-time universe membership.
- §3.2's matched controls, which need the pool of stocks *listed in that month*,
  not the pool listed today. Using today's list is the "point-in-time universe
  violation" in the §8 bias register.

Real listed counts by mid-year — note these are **not** the flat 5,000 the design
doc assumes, and using a constant overstates the funnel in every recent year:

    2015: 5,585    2019: 5,971    2021: 7,475    2023: 7,327    2026: 8,238

Two traps found by inspection, both encoded in `phase2/universe_pit.py`:

1. **`endDate` is the last observation date, not a delisting date.** Every row
   has one; live names carry roughly today's date. "Delisted" means the series
   ended materially before the file's as-of date.
2. **The list carries the final ticker; prices answer to the historical one.**
   Silicon Valley Bank appears only as `SIVBQ` (post-bankruptcy, PINK). `SIVB`
   is absent from the list entirely, yet its prices are served under `SIVB`. So
   absence from the list must not be read as "was never listed" — this is §4.4's
   ticker-reuse hazard in concrete form.

## Massive (formerly Polygon.io) — unusable here

Free "Basic" plan: **5 requests/minute**, and a rolling history window of roughly
two years. Measured as of 2026-08:

    2019-01-02 .. 2019-01-08   NOT_AUTHORIZED "your plan doesn't include this data timeframe"
    2024-01-02 .. 2024-01-05   NOT_AUTHORIZED
    2025-06-02 .. 2025-06-05   OK
    2026-06-01 .. 2026-06-04   OK

The study's formation cohorts end 2021 (5-year) / 2023 (3-year), and their
forward windows start there. The free tier cannot reach any of it. The adapter is
kept and rate-limited at 5/min, but `gate()` rejects it.

It would become useful for a *live* forward-testing extension, which is a
different study.

## yfinance — rejected, and instructively so

    AAPL   1258 rows      FRCB  1258 rows ($85.07 -> $0.04, correct)
    SIVB      0 rows      BBBYQ    0 rows
    ATVI      0 rows      TWTR     0 rows

Not "drops delisted names" but drops them **unpredictably**: First Republic is
priced correctly all the way down, while SVB, Bed Bath, Activision and Twitter
vanish. Unpredictable missingness cannot be modelled or corrected, and losing
Activision damages the *winner* tail as well as the wipeout tail.

Retained only for development. The gate fails it.

## Rate-limit discipline

`phase2/ratelimit.py` enforces every limit above with sliding windows and
persists state to `data/ratelimit_state.json`, because the limits are per-account
and reset on wall-clock boundaries — a per-process limiter would happily burn a
month's quota across three runs.

Arctic Shift has no published limit but throttles hard in practice: it 403s on
parallel requests, times out on wide windows, and needs ~1.6 s between calls.
`phase0/arctic_shift_fetch.py` is strictly serial with adaptive windows.
