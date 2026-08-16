# A1 — base-rate check: **MARGINAL** once comments are included

Full corpus: **62,519 submissions, 2010-09-29 -> 2026-08-16, zero gaps.**
Extraction at `--min-conf 0.75` → 139,491 mentions over 4,316 distinct entities.

> **Headline correction.** Earlier versions of this file reported PASS on a
> submissions-only corpus. The comments backfill is now complete (119,065
> comments, 2019-01 → 2022-01, 49,005 mentions) and it changes the verdict:
> including comments, the widest usable cohort funnels are **28.5%** (2021,
> 5-year horizon) and **30.7%** (2022, 3-year horizon) of the listed universe —
> MARGINAL rather than PASS, on both horizons. The submissions-only
> figures are retained below for comparison, not as the answer.

## Result

Denominator is the **point-in-time count of US-listed stocks** in each year
(from Tiingo's free `supported_tickers`), not a flat 5,000. The listed universe
is not constant — 5,585 names in 2015 against 8,238 in 2026 — and a fixed
denominator overstates the funnel in every recent year.

    year    mentions     >=1x     >=2x     >=5x  >=3 authors  universe   % @>=2x
    2018         129       63       19        5            6     5,321      0.4%
    2019         169       67       32        7            1     5,321      0.6%
    2020       1,187      380      178       43           32     5,337      3.3%
    2021       9,997    1,323      831      372          273     6,120     13.6%
    2022      11,650    1,390      885      386          269     6,490     13.6%
    2023       9,974    1,359      915      401          302     6,085     15.0%
    2024      25,799    2,319    1,699      866          697     5,974     28.4%
    2025      52,177    3,276    2,534    1,482        1,244     6,246     40.6%
    2026      41,636    2,912    2,332    1,171        1,011     6,926     33.7%

    GATE (5-year horizon, cohorts <= 2021): 831 names, 13.6% of 6,120  -> PASS
    GATE (3-year horizon, cohorts <= 2023): 915 names, 15.0% of 6,085  -> PASS

The denominator is **common equity only**. Tiingo labels preferred shares,
warrants, units and exchange test symbols as "Stock", and an unfiltered universe
carried ~4,000 of them. They matter in both directions: they inflate the
denominator here, and as control-group members they would have depressed the
control winner rate and inflated measured lift.

## Correction 1 — the gate must be judged on cohorts that can have outcomes

The partial-data version reported a 4.2% funnel and a clean pass. On the full
corpus the widest year is **2025 at 40.6%** — the sub now mentions roughly two fifths
of the listed universe annually. Taken at face value that is a MARGINAL,
not a pass.

It would be the wrong test. A cohort formed in 2025 has no 5-year forward return
measurable in Aug 2026, so it can never enter the study. Judging the gate on it
would kill the project over data the study could not use either way.

`a1_base_rate.py` now applies §4.3's horizons and reports the gate only over
formation cohorts that can carry a forward return. On that basis it passes at
**13.6% (5-year) and 15.0% (3-year)** — selective, though wider than the partial
data suggested.

**But the trend is itself a finding, and it is unfavourable.** The funnel widens
monotonically: 0.4% (2018) → 13.6% (2021) → 28.4% (2024) → 40.6% (2025). Whatever
this study concludes about 2019–2023 cohorts, the sub's usefulness *as a filter*
is decaying, because it increasingly mentions everything. A reader acting on a
2026 conclusion drawn from 2021 data would be using a screener that no longer
screens. That belongs in the writeup's conclusion, not a footnote.

## Correction 2 — the archived score is NOT broadly trustworthy

The partial-data version reported ~79-day median capture lag and concluded
§4.2's worry was largely misplaced. **On the full corpus that is wrong**: median
lag is 0.0 days and 75.8% of documents were captured within 24 hours of posting.

The earlier number was an artifact of only having pre-2017 data. Capture
behaviour is bimodal, and pooling hides it completely:

    2015-2022   lag 26-267 days     usable    (backfilled long after the fact)
    2023        lag 0.0, 51% <24h   UNRELIABLE
    2024-2026   lag 0.0, ~100% <24h UNRELIABLE (captured live at creation)

The recent years dominate by volume (40k of 62k documents), so the pooled figure
describes them alone. This is the same "never pool" lesson §4.2 and §8 apply to
cohorts, and it applies to data-quality diagnostics too.

**Net effect on the study: benign.** The usable formation cohorts (≤2021 for the
5-year horizon, ≤2023 for the 3-year) sit inside the trustworthy era, so an
upvote-weighted conviction measure is defensible *there*. Any extension to recent
cohorts must switch to §4.2's structural proxies. `score_check.py` now reports
per-year and refuses to give a single pooled verdict.

## The cohort-concentration warning, restated

§4.2 predicts a "5-year study" is really a study of 2020–21 picks. With the full
corpus the picture is different but no better: mentions are concentrated in
**2024–2026 (~74%)**, which is precisely the range that *cannot* be used. The
analytically usable window (2019–2023) holds ~21% of mentions.

So the binding constraint is not that the sub was small — it is that the sub got
big exactly when the horizon ran out.

## Cashtag channel confirmed as non-viable standalone

    all channels: 139,491 mentions / 4,316 entities
    cashtags only:  8,216 mentions / 1,826 entities

Cashtags carry ~6% of mentions, as §5.2 predicted.

## Caveats

- **The §5.2 gate now passes** at precision 0.952 / recall 0.930, but on 38
  documents labelled non-blind by the same system that wrote the extractor. See
  `phase1/QUALITY.md` — that is not the independent measurement §5.2 requires.
- **Submissions only — and this is now measured, not speculated.** See below.
- **≥2× is per calendar year**, not a rolling 12-month window as §6 specifies —
  slightly conservative, since it splits runs straddling a year end.
- Universe counts are US-exchange common stocks from Tiingo's ticker file.
  Names that delisted to PINK are absent from that filter, so the denominator is
  the *exchange-listed* universe, which is the right comparison for a screener.


## The verdict, on the complete corpus

Comments cover 2019-01 → 2022-01, so 2019, 2020 and 2021 are complete. On those:

    year   mentions    >=1x    >=2x   >=5x  >=3 auth  universe  % @>=2x
    2019        455     151      68     21        17     5,321     1.3%
    2020      3,984     792     386    134       161     5,337     7.2%
    2021     47,825   2,628   1,746    952       984     6,120    28.5%

    2022     68,087   2,937   1,990  1,092     1,158     6,490    30.7%

    GATE (5-year, cohorts <= 2021): 1,746 names, 28.5%  -> MARGINAL
    GATE (3-year, cohorts <= 2022): 1,990 names, 30.7%  -> MARGINAL

Both horizons land in the same place. 2022 is now complete (the comments
backfill reaches 2023-02) and is *wider* than 2021, so the 3-year horizon does
not rescue the gate — it fails it slightly harder.

**2021 is the binding cohort and it is 28.5% of the listed universe.** Reading
that plainly: in the year that matters most for a 5-year horizon, the subreddit
discussed more than a quarter of every US-listed common stock at least twice.
A funnel that wide is a weak filter. It does not make lift impossible, but it
does mean lift has to be strong to be worth anything as a screener — which is
exactly what §3.2 says to check next.

Note the scale of the shift: 2021 submissions alone carry 9,997 mentions; with
comments it is 47,825. **Comments are ~79% of 2021's mention volume.** §10's
suspicion was not merely correct, it was understated.

### Remaining caveat

2023 shows 20.0%, but the comments backfill reaches only 2023-02, so that year
is still understated. It does not change the verdict: the gate is decided by the
widest usable cohort, and both 2021 (28.5%) and 2022 (30.7%) are complete.

## §10's open question, answered: comments roughly double the funnel

A partial comments backfill (2019-01 → 2021-03, 27,580 comments → 9,382
mentions) makes the effect measurable for the two cohort years it fully covers:

    cohort  source              mentions   >=1x   >=2x   >=5x  universe  % @>=2x
    2019    submissions only         169     67     32      7     5,321      0.6%
    2019    subs + comments          455    151     68     21     5,321      1.3%
    2020    submissions only       1,192    381    180     43     5,337      3.4%
    2020    subs + comments        3,984    792    386    134     5,337      7.2%

Comments roughly **double** both the distinct-entity count and the ≥2× funnel
width. §10's suspicion that they carry most of the volume is correct.

**This threatens the A1 verdict.** The submissions-only 2021 funnel is 13.6%. If
the ~2x widening holds, the combined 2021 figure lands near 27%, which crosses
the MARGINAL boundary. The 3-year cohort (2023, 15.0% submissions-only) would be
similarly affected.

So the honest statement of the A1 result is narrower than "PASS": **the funnel is
selective enough to be worth measuring on submissions, and may not be on the full
corpus.** The comments backfill must be completed and A1 re-run before the gate
is treated as settled. That work is mechanical — the fetcher is resumable — and
is the single highest-value outstanding item after the price data.
