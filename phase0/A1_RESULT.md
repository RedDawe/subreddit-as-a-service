# A1 — base-rate check: **PASS** (provisional)

Design doc §6 runs A1 first, and §7's Phase 0 gate stops the project here if the
funnel is not meaningfully narrower than the investable universe.

**It is.** The gate passes.

## Result

Submissions only, `--min-conf 0.75`, corpus 2010-09 → 2021-mid (backfill was
still running; see *Caveats*).

    year    mentions     >=1x     >=2x     >=5x  >=3 authors  % univ @>=2x
    2015          54       17        9        2            0         0.2%
    2016          99       39       16        4            1         0.3%
    2017          66       27       14        4            2         0.3%
    2018         123       53       18        6            7         0.4%
    2019         146       54       26        6            2         0.5%
    2020       1,025      311      157       39           30         3.1%
    2021       1,570      346      212       59           36         4.2%

Widest annual ≥2× funnel: **212 names, 4.2% of a ~5,000-name universe.**

This is the shape §1.1 describes as useful — "a candidate set of a few hundred
names instead of several thousand". Conditioning on the sub is genuinely
selective, so lift has room to exist and is worth measuring.

Requiring three *distinct* authors (the design doc's preferred weighting, §5.4)
narrows it much further: **36 names in 2021, 0.7% of the universe.** If lift
survives at that threshold it would be a strong screener; if it only appears at
≥1× it is probably coincidental coverage.

## What this does and does not establish

It establishes that the funnel is **narrow**. It says nothing about whether the
names in it are **good** — that is A2 onward and needs the price data.

A pass here is not a positive result about the subreddit. It is the removal of
the cheapest reason to stop.

## The cohort-concentration warning is confirmed, and it is severe

§4.2 and §8 flag that the sub grew massively post-2020 and that a "5-year study"
is really a study of 2020–21 picks. The data is blunter than the doc anticipated:

    2019:    146 mentions
    2020:  1,025 mentions   (7x in one year)
    2021:  1,570 mentions

**~84% of all mentions in this corpus fall in 2020–2021.** Every pre-2019 cohort
is too thin to carry a lift estimate on its own — 2015–2019 together produce
fewer mentions than a single month of 2021.

Two consequences, both of which should be settled before A2 runs:

1. Pooling cohorts is not an option, it is a category error. A pooled number
   would be a 2020–21 number wearing a decade's clothing.
2. §4.3's horizon constraint bites harder than the doc estimates. A 5-year hold
   measured from Aug 2026 needs formation cohorts ending Aug 2021 — which is
   *precisely* where this corpus becomes usable. The 5-year analysis therefore
   rests almost entirely on 2020–21 formation, i.e. on names discussed during a
   liquidity boom and measured across its unwind. The 3-year horizon (§4.3's own
   mitigation) is not a robustness check here; it is the primary analysis.

## Cashtag channel is not a viable standalone

    all channels: 3,090 mentions / 593 entities
    cashtags only:  125 mentions /  77 entities

Cashtags carry ~4% of mentions. §5.2 predicted this ("high precision, low
recall") and it is why the company-name channel exists. Anyone tempted to run a
cheap `\$[A-Z]{1,5}` study of this sub would be working with 4% of the evidence.

## Caveats

- **The §5.2 extraction gate has not run.** These counts inherit whatever
  precision/recall the extractor actually has, which is unmeasured until 300
  documents are hand-labelled. Known FP classes found and fixed are in
  `phase1/QUALITY.md`; the residual class is uncorroborated domain acronyms.
- **Submissions only.** §10 notes comments carry most of the volume and most of
  the bear cases. Adding them will widen every count, and may widen the funnel
  enough to weaken this gate — it should be re-run after the comments backfill.
- **≥2× is per calendar year**, not a rolling 12-month window as §6 specifies.
  Calendar-year buckets split runs that straddle a year end, so this slightly
  *under*-counts. The direction is conservative for a gate that already passes.
- The 5,000-name universe denominator is an order-of-magnitude figure, not a
  point-in-time count. Nothing here turns on its exact value.
