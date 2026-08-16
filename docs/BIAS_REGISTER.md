# Bias register

Design doc §8 requires every known bias to be tracked with its direction, and
the residual direction stated in the conclusion. This is that register, updated
with what was actually found rather than what was anticipated.

**Legend:** *Flatters* = pushes the result toward "the sub is useful".

## Biases from the design doc

| # | Bias | Direction | Status |
|---|---|---|---|
| 1 | Survivorship in price data | Flatters | **Handled.** Tiingo passes a delisting gate that checks series *terminate on the real last trade date*, not merely that rows exist. |
| 2 | Deleted / removed posts | Flatters | **Quantified** — see below. 24% of formation-window posts have lost their body; they yield mentions at 49% the rate of intact posts. |
| 3 | Point-in-time universe violation | Flatters | **Handled for controls.** Drawn from names listed at the start of the formation window, so dead names can be sampled. |
| 4 | Size / sector skew of the sub | Unknown | **Size adjusted; sector measured, not adjusted.** See below — the "no free sector source" claim was wrong. |
| 5 | Benchmark choice | Hurts | SPY reported; VTV/IWD fetched; factor-adjusted alpha implemented. |
| 6 | Cohort concentration in 2020–21 | Unknown | **Worse than expected**, see below. |
| 7 | Multiple hypothesis testing | Flatters | A1–A8 are pre-specified by the doc. No adjusted p-values computed; treat individual CIs as unadjusted. |
| 8 | Look-ahead in outcome labels | Flatters | **Handled.** Labels computed strictly forward from the formation month. |

## Biases found during implementation that the doc did not anticipate

| # | Bias | Direction | Status |
|---|---|---|---|
| 9 | **Survivorship in *extraction*** | Flatters | **Found and fixed.** SEC's current-state ticker file omits acquired/delisted companies, so `$FL` (Foot Locker, acquired 2025) was unmatchable in a 2022 post. The *mention set itself* was shedding exactly the acquired and bankrupt names the study needs. Fixed by topping the vocabulary up from Tiingo's delisted-inclusive file (10,398 → 19,353 symbols). This is distinct from bias #1 and would have left no trace. |
| 10 | **Research vendors counted as holdings** | Unclear, distorting | **Mitigated.** Morningstar contributed 698 mentions — top-ten by volume — almost all citations ("Morningstar Price/Fair Value: 0.64"). Now demoted unless investment framing is present. Distorts per-name statistics rather than the aggregate. |
| 11 | **Ticker lists unread** | Hurts (recall) | **Fixed.** Comma- and newline-separated holdings lists were largely unparsed; one 15-name portfolio list yielded zero. Since such lists skew toward mainstream dividend names, missing them biased the mention set toward whatever the prose channel caught. |
| 12 | **Aboutness vs mention** | Flatters | **Open, unfixed.** The extractor detects mentions, not what a document is *about*. "Worked 10 years at Procter & Gamble" in a Johnson Outdoors writeup counts as a P&G mention. Inflates mention counts for large, frequently-name-dropped companies. |
| 13 | **Non-US names invisible** | Unknown | **Structural, disclosed.** SEC-based resolution means foreign-only listings cannot be extracted. H3/A5's non-US leg is declined rather than reported as 0%. |
| 14 | **Score reliability is era-dependent** | Neutral here | **Handled by scoping.** Archived scores settled for 2015–2022 but are captured at creation from 2023 on. Usable cohorts sit in the trustworthy era. |
| 15 | **Self-labelled validation** | Flatters | **Open.** The §5.2 gate passes at 0.955/0.933, but on n=45 labelled by the same system that wrote the extractor, non-blind. Not the independent measurement the doc requires. |
| 16 | **Post-stratification ≠ matching** | Unknown | **Substitution, disclosed.** k=5 matched controls are unaffordable on a 500-symbol/month quota. Post-stratification adjusts for size only; matching would also have covered sector and country. |
| 17 | **Control formation dates** | Unknown | **Fixed.** Random draws match the treated calendar only in expectation; at n=220 the realised mix can drift. Dates are now assigned by walking the sorted treated dates in step, so the marginal distributions match by construction — max monthly share discrepancy 0.41%, annual mix 14.4/50.7/34.9 treated vs 14.5/50.9/34.5 control. This matters because 2019, 2020 and 2021 entry points had very different forward markets. |
| 18 | **Name channel is survivor-only** | Flatters | **Quantified, unfixed.** 46% of the ticker vocabulary (8,955 of 19,353) has no company name, because the delisted top-up supplies tickers only. A dead company is findable as `GRIN` but not as "Grindrod". In the 2019-2021 cohorts, 243 of 1,507 entities (16.1%) are ticker-only. Dead names skew to the wipeout tail, so this thins losers more than winners. Fix rejected as disproportionate — see `phase1/QUALITY.md`. |
| 19 | **Preferreds/warrants in the control pool** | Flatters | **Found and fixed.** Tiingo types preferred shares, warrants, units and exchange test symbols as "Stock". Preferreds are bond-like: they rarely 3x and rarely wipe out, so seeding controls with ~4,000 of them would have depressed the control winner rate and inflated lift. |

## Bias #4: sector is measurable after all, and the skew is modest

An earlier version of this register said sector could not be controlled for want
of a free source. That was wrong. SEC's quarterly Financial Statement Data Sets
carry `cik`, `sic` and `countryba` for every filer, as a bulk ZIP with no key and
no rate limit (`phase2/sectors.py`).

Sector mix, treated vs the control draw, by SEC SIC division:

    division                  treated  control
    manufacturing               26.3%    21.8%
    finance_insurance_re        13.9%    15.0%
    services                    11.0%    10.9%
    retail                       7.2%     2.3%
    transport_utilities          7.2%     4.1%
    mining                       1.4%     0.5%
    construction                 1.0%     0.9%
    wholesale                    0.5%     0.9%
    unknown                     31.6%    43.6%

The standout is **retail, where the subreddit is ~3x overweight** — consistent
with a forum that discusses consumer-facing businesses it can reason about from
experience. Transport/utilities is also overweight. Finance and services, the
two largest sectors after manufacturing, are well matched.

Sector is **not** added to the lift estimator, and that is a deliberate call
rather than an oversight: crossing 5 size strata with ~9 sector divisions gives
45 cells against ~220 controls, roughly 4 per cell. That produces noise, not
adjustment. Reporting the imbalance makes the residual confound explicit, which
is the honest option at this sample size; closing it needs either a larger
control sample (more quota) or the doc's original 1:k matching.

Coverage caveat: sector is known for 68% of treated and 56% of controls. The map
is built from one quarter of filers, and delisted names have no CIK at all, so
"unknown" correlates with being dead — which is itself the #18 asymmetry.

## Bias #2 quantified: deleted and removed content

Across the whole corpus, 20.4% of submissions have a `[deleted]`/`[removed]`
body. In the 2019–2021 formation window the picture is:

    formation-window posts                8,641
      body gone                           2,072   24.0%
        author-deleted   ("deleted")      1,141   13.2%
        moderator-removed                   829    9.6%
        reddit/admin-removed                272    3.1%
    author account deleted (corpus-wide)  3,551

The three causes are not equivalent. Moderator and admin removals are mostly
rule-breaking and spam, which has no obvious relationship to whether a stock
call was good. **Author deletions are the survivorship-relevant class** — §4.2's
concern is that people quietly delete their own bad calls — and those are 13.2%
of the formation window.

The damage to extraction is partial, because Reddit deletes the body but keeps
the title:

    body-gone posts yielding >=1 mention    365 / 2,072   17.6%
    intact posts yielding >=1 mention     2,342 / 6,569   35.7%

So body-gone posts still produce mentions at **49% the rate** of intact ones.
Roughly half the mention-bearing content of deleted posts survives in the title.

Direction and size: if deleted posts skew toward bad calls, this removes losers
preferentially and **flatters the subreddit**. The upper bound on the effect is
the ~18 percentage-point mention-rate gap applied to 2,072 posts — on the order
of 375 posts' worth of mentions, against 8,641 posts in the window. Material but
not dominant, and it cannot be corrected, only disclosed.

## The cohort problem, restated

§4.2 predicted a "5-year study" would really be a study of 2020–21 picks. The
full corpus says something sharper and worse:

    2019-2023 (analytically usable)  ~21% of mentions
    2024-2026 (cannot be used yet)   ~74% of mentions

The subreddit became large exactly when the measurement horizon ran out. So the
study's statistical power is permanently capped by an accident of timing, not by
data access. No amount of extra quota fixes this; only waiting does.

## Residual direction

Counting only what is **open and unfixed** — #12 (aboutness), #15 (self-labelled
validation), #7 (unadjusted multiplicity) all flatter; #16 and #17 are of
unknown sign; #11 was a *hurting* bias and has been fixed.

Add #18 (name channel survivor-only, quantified at 16.1% of cohort entities)
to the flattering side.

**The residual bias points toward flattering the subreddit.** Any positive lift
should therefore be read as an upper bound, and a null result as robust.
