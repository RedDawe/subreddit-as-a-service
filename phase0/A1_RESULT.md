# A1 — base-rate check: **PASS on usable cohorts**, with a large caveat

Full corpus: **62,519 submissions, 2010-09-29 → 2026-08-16, zero gaps.**
Extraction at `--min-conf 0.75` → 139,491 mentions over 4,316 distinct entities.

> **This supersedes an earlier version of this file written from a partial
> backfill (through mid-2021). Two of its conclusions were wrong. Both
> corrections are stated explicitly below rather than quietly edited out.**

## Result

    year    mentions     >=1x     >=2x     >=5x  >=3 authors  % univ @>=2x
    2018         123       53       18        6            7         0.4%
    2019         149       56       27        6            2         0.5%
    2020       1,047      316      161       40           30         3.2%
    2021       9,120    1,091      721      333          233        14.4%
    2022      10,441    1,187      785      358          241        15.7%
    2023       9,150    1,162      810      374          276        16.2%
    2024      23,764    2,024    1,541      812          640        30.8%
    2025      48,276    2,904    2,309    1,386        1,150        46.2%
    2026      37,186    2,487    1,955    1,074          906        39.1%

    GATE (5-year horizon, cohorts <= 2021): 721 names, 14.4%  -> PASS
    GATE (3-year horizon, cohorts <= 2023): 810 names, 16.2%  -> PASS

## Correction 1 — the gate must be judged on cohorts that can have outcomes

The partial-data version reported a 4.2% funnel and a clean pass. On the full
corpus the widest year is **2025 at 46.2%** — the sub now mentions nearly half
the investable universe annually. Taken at face value that is close to a fail.

It would be the wrong test. A cohort formed in 2025 has no 5-year forward return
measurable in Aug 2026, so it can never enter the study. Judging the gate on it
would kill the project over data the study could not use either way.

`a1_base_rate.py` now applies §4.3's horizons and reports the gate only over
formation cohorts that can carry a forward return. On that basis it passes at
14.4% (5-year) and 16.2% (3-year) — selective, though four times wider than the
partial data suggested.

**But the trend is itself a finding, and it is unfavourable.** The funnel widens
monotonically: 0.4% (2018) → 14.4% (2021) → 30.8% (2024) → 46.2% (2025). Whatever
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

- **The §5.2 extraction gate has still not run.** It needs 300 hand-labelled
  documents. Everything above inherits unmeasured precision/recall. Known FP
  classes found and fixed are in `phase1/QUALITY.md`.
- **Submissions only.** §10 is right that comments carry most of the volume and
  most of the bear cases. Adding them will widen every count and may move the
  gate toward MARGINAL even on usable cohorts. This must be re-run after the
  comments backfill.
- **≥2× is per calendar year**, not a rolling 12-month window as §6 specifies —
  slightly conservative, since it splits runs straddling a year end.
- The 5,000-name universe denominator is an order-of-magnitude figure.
