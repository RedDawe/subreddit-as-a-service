# Bias register

Design doc §8 requires every known bias to be tracked with its direction, and
the residual direction stated in the conclusion. This is that register, updated
with what was actually found rather than what was anticipated.

**Legend:** *Flatters* = pushes the result toward "the sub is useful".

## Biases from the design doc

| # | Bias | Direction | Status |
|---|---|---|---|
| 1 | Survivorship in price data | Flatters | **Handled.** Tiingo passes a delisting gate that checks series *terminate on the real last trade date*, not merely that rows exist. |
| 2 | Deleted / removed posts | Flatters | **Counted, not corrected.** `n_removed` is in the panel. Quantification pending. |
| 3 | Point-in-time universe violation | Flatters | **Handled for controls.** Drawn from names listed at the start of the formation window, so dead names can be sampled. |
| 4 | Size / sector skew of the sub | Unknown | **Partly handled.** Post-stratified on dollar-volume quintiles. Sector is NOT controlled — no free sector source. |
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
| 17 | **Control formation dates assigned by draw** | Unknown | Controls inherit formation dates sampled from the treated distribution, so calendar exposure matches in aggregate but not name-by-name. |
| 18 | **Name channel is survivor-only** | Flatters | **Quantified, unfixed.** 46% of the ticker vocabulary (8,955 of 19,353) has no company name, because the delisted top-up supplies tickers only. A dead company is findable as `GRIN` but not as "Grindrod". In the 2019-2021 cohorts, 243 of 1,507 entities (16.1%) are ticker-only. Dead names skew to the wipeout tail, so this thins losers more than winners. Fix rejected as disproportionate — see `phase1/QUALITY.md`. |
| 19 | **Preferreds/warrants in the control pool** | Flatters | **Found and fixed.** Tiingo types preferred shares, warrants, units and exchange test symbols as "Stock". Preferreds are bond-like: they rarely 3x and rarely wipe out, so seeding controls with ~4,000 of them would have depressed the control winner rate and inflated lift. |

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
