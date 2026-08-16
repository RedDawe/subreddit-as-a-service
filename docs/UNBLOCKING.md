# What is still needed, and how to supply it

**The price-data blocker is resolved on a free tier.** What remains is a quota
constraint, one deferred decision, and one cheap free credential.

| Was | Now |
|---|---|
| price data with delisting returns | **solved free** via Tiingo (`docs/DATA_SOURCES.md`) |
| point-in-time universe | **solved free** via Tiingo `supported_tickers` |
| stance classification | **deferred by decision**; free options to be evaluated later |
| Reddit OAuth for the §4.2 gate | still open, free, 2 minutes — see below |
| 500 unique symbols/month | the real remaining constraint on pace |

## Blocker 1 — price data: **RESOLVED, free**

Tiingo's free tier passes the delisting gate, including terminating each series
on the real last trade date rather than forward-filling. Its static
`supported_tickers` file additionally supplies a free point-in-time universe.
Full measurements in `docs/DATA_SOURCES.md`.

No subscription is needed for the US-only pass the design doc's §10 recommends
running first. The only cost is time: the free tier allows **500 unique symbols
per month**, so a full pass spans several months and symbols must be spent
deliberately (`phase2/ratelimit.py` tracks the budget persistently).

Massive/Polygon's free tier is *not* usable — a rolling ~2-year window that
cannot reach the study's formation cohorts.

## Blocker 2 — stance classification (deferred)

Deferred by decision. §5.3 requires an LLM pass and rules out lexicon sentiment,
so `phase2/stance.py` keeps the keyword baseline firewalled behind `--force` and
stamps `method` into every row. When this is picked up, free/local options are
worth evaluating before a paid key.

Everything upstream of stance runs without it. H1 on all-mentions is the
robustness check the doc already specifies; only the bullish-only headline is
blocked.

## Blocker 3 — Reddit OAuth: **abandon this, it is closed**

Do not keep trying — the failure is not on your end. Reddit's **Responsible
Builder Policy** disabled self-serve app creation. The `prefs/apps` page is left
in a half-working state: the Create button silently refreshes, "accept terms"
checkboxes are missing, and the policy link is shown instead of an app. Data API
access is now behind manual approval, and existing apps keep working while new
ones cannot be self-issued.

So the §4.2 live score comparison ("sample 50 old posts, compare dump score to
the live thread") is **not obtainable** on the free path. Treat it as closed
rather than pending.

The loss is small and bounded, because `retrieved_on` already answers the
question without Reddit:

    2015-2022   lag 26-267 days     scores settled   -> usable
    2023-2026   lag ~0 days         captured live    -> unusable

The study's usable formation cohorts end 2021 (5-year) / 2023 (3-year), i.e.
inside the trustworthy era. The live check would have confirmed that; it would
not have changed it. The writeup should state this as an unverified assumption
rather than a measured fact.

## Structural limitation: H3 / A5 is not measurable as built

Design doc §1.3's novelty hypothesis asks what share of mentions are **non-US
listed**. That cannot currently be answered, and the reason is structural rather
than a missing key.

Entity resolution runs off SEC EDGAR, whose exchange file contains only Nasdaq
(4,347), NYSE (3,312), OTC (2,514) and CBOE (28) — all US listings. A company
listed only in Frankfurt, Tokyo or Warsaw has no CIK and therefore cannot be
extracted at all. ADRs are covered; genuine foreign listings are invisible.

So a measured "0% non-US" would be an artifact of the universe, not a finding
about the subreddit. To answer H3 honestly the alias dictionary needs a non-US
identifier source (ISIN- or FIGI-based). Until then A5 should report only the
S&P-500 and top-1000 splits and explicitly decline the non-US question.

## Handing over credentials

Do not paste keys into chat and do not commit them. Two options:

1. **Environment variables** at claude.ai/code → your environment → Environment
   variables. Editable from mobile Safari, never enters the transcript, survives
   container restarts. Preferred.
2. A local `.env` in the repo root — already gitignored, and verified excluded.

Variables this repo reads:

| Variable | Unblocks | Read by |
|---|---|---|
| `TIINGO_API_KEY` | price data + point-in-time universe | `phase2/prices.py` |
| `MASSIVE_API_KEY` | recent-window prices only (not usable here) | `phase2/prices.py` |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | the §4.2 score gate | `phase0/score_check.py` |
| `NASDAQ_DATA_LINK_API_KEY` | optional paid upgrade | `phase2/prices.py` |
| `SEC_UA` | optional contact string for SEC | `phase1/universe.py` |

If a key is ever exposed, rotate it at the vendor rather than deleting the
message.

## The Oracle VM

Still not needed. The comments backfill is the only long job, and the fetcher is
checkpointed and resumable across sessions here.
