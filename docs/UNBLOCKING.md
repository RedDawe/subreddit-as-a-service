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

## Blocker 3 — Reddit OAuth for the §4.2 score gate

Still open, still cheap, and now better motivated: on the full corpus the
archived score IS unreliable from 2023 onward (median capture lag 0.0 days,
~100% captured within 24h), though it remains trustworthy for the cohorts this
study can actually use. A live comparison would confirm the split.

**To create the app** (reddit.com → preferences → apps → create another app):

    name          value
    ----          -----
    type          script
    redirect uri  http://localhost:8080/reddit_callback
    about url     (leave blank - optional for script apps)

`redirect uri` is mandatory even for script-type apps, but it is never actually
visited under the client-credentials flow this repo uses — it just has to be a
syntactically valid URL you control. `http://localhost:8080/reddit_callback` is
fine and needs nothing running on that port.

Then set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`.

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
