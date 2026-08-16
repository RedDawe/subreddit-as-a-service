# Is r/ValueInvesting a useful idea screener?

Implementation of the design doc: a **screener evaluation**, not a portfolio
backtest. The governing question is whether conditioning on "this name appeared
in the sub" raises the density of future winners enough to be worth using as a
funnel — measured as lift against *matched* controls, not against a random draw
from the whole market.

## Status

| Phase | State |
|---|---|
| 0 — acquisition, A1 base rate, score-reliability gate | **built and running** |
| 1 — extraction, entity resolution, panel | **built**; formal precision/recall gate needs human labels |
| 2 — stance, returns | **blocked on credentials**, code written and gated |
| 3 — analyses A2–A8 | not started (blocked behind Phase 2) |

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

**Price data.** §4.4 predicted free sources would drop delisted names. They do —
but *unpredictably*, which is worse. First Republic is priced correctly all the
way down to $0.04 while SVB, Bed Bath, Activision and Twitter return nothing.
Unpredictable missingness cannot be modelled, and losing Activision means the
*winner* tail is damaged too, not just the wipeout tail. `phase2/prices.py`
therefore refuses to compute returns from a source that fails a delisting gate.

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
      stance.py               §5.3 LLM stance pass + firewalled baseline
    docs/
      UNBLOCKING.md           what is still needed, and how to hand it over

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

Use `--min-conf 0.75`. See `phase1/QUALITY.md` for why.

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

## What this cannot tell you yet

A1 measures whether the funnel is *narrow*. It says nothing about whether the
names in it are *good* — that is A2 onward, and it needs the price data. The
honest kill-gate order from §7 still applies: A1, then the extraction gate, then
decide whether the price-data subscription is justified.
