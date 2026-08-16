# Is r/ValueInvesting a useful idea screener?

Implementation of the design doc: a **screener evaluation**, not a portfolio
backtest. The governing question is whether conditioning on "this name appeared
in the sub" raises the density of future winners enough to be worth using as a
funnel — measured as lift against *matched* controls, not against a random draw
from the whole market.

## Status

| Phase | State |
|---|---|
| 0 — acquisition, A1, score gate | **done.** 62,519 submissions (2010-09 → 2026-08) + 119,065 comments (2019 → 2022), no gaps |
| 1 — extraction, entity resolution, panel | **done.** §5.2 gate **passes** at precision 0.955 / recall 0.933 (n=45, self-labelled) |
| 2 — price data | **done.** Free tier passes the delisting gate; point-in-time universe built |
| 3 — analyses A2–A8 | **code complete and unit-tested; running.** Blocked only on a 50-request/hour fetch quota |

Headline: with comments included, the binding cohorts are **28.5%** (2021,
5-year) and **33.3%** (2023, 3-year) of the point-in-time listed universe —
**MARGINAL on both horizons**, not the PASS that submissions alone suggested. In the year that matters most for a 5-year horizon,
the sub discussed more than a quarter of every US-listed common stock at least
twice. Comments are ~79% of 2021's mention volume. See `phase0/A1_RESULT.md`.

**The lift question (A2–A8) is not yet answered.** All code is written and
unit-tested; it is waiting on price data at 50 symbols/hour.

`phase0/FEASIBILITY.md` records what was probed in this environment and what
that changed about the plan. `docs/UNBLOCKING.md` is the short version of what
is needed to finish, and how to supply it safely.

## The two things that changed from the design doc

**Acquisition.** §4.1's sources are torrent-distributed and BitTorrent is
blocked here (ports 80/443 only). The Arctic Shift REST API replaces them and is
strictly better for this study: it reaches back to the sub's first post in
September 2010, is live to the present, and therefore collapses the doc's
separate "gap fill 2025→present" step and its zstd parsing stage into one
source.

**Price data.** §4.4 assumed delisting-inclusive pricing had to be bought. It
does not: **Tiingo's free tier passes the delisting gate**, and each series ends
when the company actually stopped trading rather than being forward-filled
(Activision terminates on the Microsoft close, Twitter on the take-private). Its
static ticker file additionally provides a free **point-in-time universe**, which
is what §3.2's matched controls need. The real constraint is a quota — 500 unique
symbols per month — not money. `docs/DATA_SOURCES.md` has the measurements.

yfinance is still rejected: it drops delisted names *unpredictably* (First
Republic priced correctly to $0.04, while SVB, Bed Bath, Activision and Twitter
vanish), damaging the winner tail as well as the wipeout tail.

## Layout

    phase0/
      arctic_shift_fetch.py   resumable, rate-limit-aware backfill
      score_check.py          §4.2 gate: is the archived score trustworthy?
      a1_base_rate.py         A1 funnel width + explicit gate verdict
      FEASIBILITY.md          what this environment can and cannot do
    phase1/
      universe.py             SEC EDGAR ticker -> CIK, company aliases
      stoplist.py             three evidence tiers for ambiguous tokens
      extract.py              three-channel extraction (stages 2-3)
      build_panel.py          the (entity x month) mention panel (stage 5)
      make_label_sample.py    year-stratified sample for the §5.2 gate
      score_labels.py         precision/recall scorer for that gate
      QUALITY.md              false-positive classes found and fixed
    phase2/
      prices.py               gated price adapters (§4.4 + §7 Phase 2 gate)
      ratelimit.py            persistent vendor quota + rate limiting
      universe_pit.py         point-in-time listed universe (§3.2, §4.4)
      stance.py               §5.3 LLM stance pass + firewalled baseline
    phase3/
      select_cohort.py        treated set + control sample within quota
      fetch_prices.py         resumable, quota-aware price fetch
      outcomes.py             forward returns + winner/wipeout labels (§3.1)
      analyses.py             A2 lift, A3 recall, A7 portfolio, A8 dose
      analyses_extra.py       A4 timing, A5 novelty, A6 screens, A7 alpha
      factors.py              FF5 + momentum (Ken French, free)
      writeup.py              assembles the final report from results
      test_outcomes.py        8 tests on the delisting/acquisition paths
      test_analyses.py        6 tests on the lift estimator
    docs/
      DATA_SOURCES.md         every source, its limits, and what it can do
      BIAS_REGISTER.md        §8 register - 8 doc biases + 11 found in build
      UNBLOCKING.md           what is still needed, and how to hand it over
    artifacts/
      mention_panel.csv       deliverable #1 - 27,437 (entity x month) rows
      label_sample.tsv        300 docs awaiting hand labels for the §5.2 gate

## Running it

    # 1. backfill (resumable - just re-run to continue)
    python3 phase0/arctic_shift_fetch.py posts 2010-09-01 2026-08-16 data/posts

    # 2. is the archived score usable as a conviction proxy?
    python3 phase0/score_check.py data/posts/posts.ndjson

    # 3. extract mentions
    PYTHONPATH=phase1 python3 phase1/extract.py \
        data/posts/posts.ndjson data/mentions_posts.ndjson post

    # 4. A1 - the first kill gate
    python3 phase0/a1_base_rate.py data/mentions_posts.ndjson 0.75

    # 5. the panel (deliverable #1)
    python3 phase1/build_panel.py data/mentions_posts.ndjson data/mention_panel.csv \
        --posts data/posts/posts.ndjson --min-conf 0.75

    # 6. the §5.2 validation gate - needs human labelling in between
    python3 phase1/make_label_sample.py data/posts/posts.ndjson data/labels.tsv --n 300
    python3 phase1/score_labels.py data/labels.tsv data/mentions_posts.ndjson

    # 7. the lift analysis (resumable; ~50 symbols/hour)
    ./phase3/run_all.sh

Use `--min-conf 0.75`. See `phase1/QUALITY.md` for why.

## Tests

    python3 phase3/test_outcomes.py    # 8/8 - delisting, acquisition, horizons
    python3 phase3/test_analyses.py    # 6/6 - post-stratified lift estimator

## Design commitments carried through

- Mentions resolve to **CIK**, never to a ticker string (§4.4).
- Results are reported **by cohort year**, never pooled only (§4.2, §8).
- The archived `score` travels with a `score_lag_days_median` column so its
  reliability can be judged rather than assumed (§4.2).
- Removed/deleted content is **counted**, because that bias cannot be quantified
  later if it is not recorded now (§4.2, §8).
- Stance columns are left **null**, not zero, until a real stance pass runs —
  zeros would read as measured neutrality (§5.3).
- The keyword stance baseline is firewalled behind `--force` and stamps its
  method into every row, so floor-quality labels cannot be mistaken for the LLM
  pass the doc requires (§5.3).

## Known structural limitations

- **H3 / A5 (non-US novelty) is unmeasurable as built.** Entity resolution is
  SEC-based, so only US listings and ADRs exist in the universe. A "0% non-US"
  result would be an artifact. Needs an ISIN/FIGI source to answer honestly.
- **The §4.2 live score check is closed**, not pending: Reddit disabled
  self-serve API app creation (Responsible Builder Policy, 2026).
- **Research-vendor mentions** (Morningstar, FactSet, MSCI…) are demoted by a
  heuristic standing in for the §5.3 role/stance judgement.

## What this cannot tell you yet

A1 measures whether the funnel is *narrow*. It says nothing about whether the
names in it are *good* — that is A2 onward, and it needs the price data. The
honest kill-gate order from §7 still applies: A1, then the extraction gate, then
decide whether the price-data subscription is justified.
