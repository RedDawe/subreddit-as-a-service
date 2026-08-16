# Is r/ValueInvesting a useful idea screener?

**Answer: no, not on this evidence.** The funnel is too wide to filter much, the
lift on winners is statistically indistinguishable from zero, the only
significant effect is on *losers*, and the sub arrives after the move has
started.

Every number below is reproducible from this repo (`phase3/run_all.sh`).

---

## 1. The headline

| test | 5-year | 3-year |
|---|---|---|
| **A1** funnel width (binding cohort) | 28.5% of the listed universe | 33.3% |
| **A2** adjusted lift, `winner_3x` | 1.62 **[0.83, 4.20]** | 2.31 **[0.61, 8.50]** |
| **A2** adjusted lift, `outperformer` | 0.86 **[0.56, 1.83]** | 1.01 **[0.62, 2.01]** |
| **A2** adjusted lift, `wipeout` | **2.08 [1.09, 3.94]** | **2.85 [1.46, 5.88]** |

Sample: 193 treated names (≥4 distinct submission authors, formation 2019–2021)
against 188 controls drawn from the point-in-time listed universe, size-adjusted
by post-stratification on dollar-volume quintiles.

**Winners: null.** Both horizons' confidence intervals span 1.0. §3.2 states the
conclusion for this case outright — *"if matched lift is indistinguishable from
zero … the honest conclusion is 'just use a screener'."*

**Outperformance: null, and flat.** 0.86 and 1.01. Conditioning on the sub does
not raise the odds of beating SPY.

**Wipeouts: significant, and the wrong way.** Size-adjusted, the sub's names are
**2.1× (5y) and 2.9× (3y) more likely to lose 70%+**, and both intervals exclude
1.0. This is the only tail the data can distinguish.

That combination is precisely §3.1's warning: *"a funnel that enriches for both
tails is a volatility filter, not a skill filter."* Here it does not even enrich
both tails — only the losing one, significantly.

### Why the naive number misleads

    winner_3x    naive lift 1.35   →   adjusted 1.62
    wipeout      naive lift 0.69   →   adjusted 2.08

Raw, the sub's names look *safer* than controls (9.8% wipeouts vs 14.4%). That
is entirely a size effect: controls include small illiquid names that fail often.
Reweighted to the sub's own size distribution, the expected control wipeout rate
falls to 4.7% — and the sub's 9.8% is then twice that. **The sign flips.** This
is exactly why §3.2 insists on matched rather than naive comparison.

---

## 2. The sub follows price (A4)

Of 181 treated names that had a ≥50% move:

    first mentioned AFTER the move began : 77.9%
    lag from trough to first mention     : median +225 days (p25 +51, p75 +314)

**More than three-quarters of the time, the run-up was already ~7 months old
before the sub discussed the name.** Whatever the sub is doing, it is not
early.

---

## 3. Conviction does carry signal (A8)

The one genuinely encouraging result. Splitting the treated set by distinct
author count, 3-year horizon:

    authors     n   winner_3x   wipeout   median return
      3-4      61       1.6%     19.7%        +16.2%
      5-9      76       1.3%      6.6%        +20.8%
     10-19     35       0.0%      2.9%        +31.1%

**The wipeout rate falls sevenfold as author count rises, and median return
roughly doubles.** So the aggregate wipeout result is driven by the
low-conviction tail: names three or four people mentioned once. Names a dozen
people discussed did not blow up.

That is a real, monotone dose-response — the pattern §6's A8 says to look for.
It does not rescue the winner-lift null, but it says the sub's *high-conviction*
subset is not the problem. The screener, if there is one, is "names ≥10 different
people discussed", not "names that appeared".

---

## 4. Recall says the sub is measuring its own breadth (A3)

3-year horizon, within the sampled universe:

    class            n    mentioned   recall
    winner_3x       15        6        40.0%
    wipeout         38       18        47.4%
    outperformer   135       74        54.8%
    all names      381      193        50.7%

**Winner recall (40.0%) is *below* loser recall (47.4%) and below the overall
mention rate (50.7%).** §1.2 sets exactly this test: *"if 90% of winners appeared
and 88% of losers appeared too, the sub has measured nothing but its own
breadth."* The sub does not preferentially surface winners. It slightly
preferentially surfaces losers.

---

## 5. Novelty and the trivial screen (A5, A6)

    confidently in the S&P 500 at formation   47.2%
    upper bound on "outside the S&P 500"      52.8%   (48.2pp of it unknown)
    in the top dollar-volume quintile         36.8%
    above the universe median                 76.2%

Novelty is an **upper bound**: the constituent list is a current snapshot, so a
2021 member since removed reads as a non-member. The true novelty share is lower
than 52.8%.

Head-to-head against "just buy the big liquid names" (A6, 5-year):

    outcome         sub    big-liquid screen   ratio
    winner_3x     15.0%          10.8%          1.39
    outperformer  35.2%          32.4%          1.09
    wipeout        9.8%           2.7%          3.64

The sub beats the trivial screen slightly on winners and **loses badly on
wipeouts**. Baselines 2 and 3 from §3.2 (news coverage, mechanical value screen)
were not run — both need fundamentals the free tier does not carry.

---

## 6. Portfolio and factor alpha (A7)

Equal-weighted, 5-year hold, regressed on Fama-French 5 + momentum over 87
months:

    monthly alpha    +0.313%   (annualised +3.82%)
    t-stat            +1.19    (not significant)
    beta Mkt-RF       +0.955
    beta SMB          +0.610
    beta HML          -0.122
    beta CMA          +0.412

Alpha is positive but insignificant. The interesting number is **SMB +0.61**: the
portfolio carries a large small-cap tilt, and **HML is slightly negative** — for a
*value* subreddit, the book carries no value loading at all. Much of the raw
return is a size bet.

t-stat uses iid residual standard errors with no Newey-West correction, so treat
it as indicative.

---

## 7. What would change this answer

In rough order of how much they matter:

1. **Sample size.** 193 treated names gives intervals like [0.83, 4.20]. The
   quota (500 unique symbols/month) is the binding constraint, not money — three
   more months of fetching would roughly quadruple the sample.
2. **Stance classification (§5.3).** This is *all-mentions*, which §5.3 calls the
   robustness check, not the headline. Bullish-only could differ, and given A8's
   dose-response it plausibly would.
3. **Independent extraction labels.** The gate passes at 0.955/0.933 but on 45
   documents labelled non-blind by the same system that wrote the extractor.
4. **1:k matching instead of post-stratification**, which would also control
   sector and country rather than size alone.

## 8. Residual bias

`docs/BIAS_REGISTER.md` tracks 8 biases from the design doc and 11 found during
implementation. Of those still open and unfixed — aboutness, self-labelled
validation, name-channel survivorship, unadjusted multiplicity — **all point
toward flattering the subreddit.**

So: the null on winners is robust (a favourable bias failed to produce a
positive), and the significant wipeout result is, if anything, understated.

## 9. The finding that outlives the study

The funnel has widened every single year:

    2019   1.3%      2022  30.7%
    2020   7.2%      2023  33.3%
    2021  28.5%      2025  40.7%

By 2025 the subreddit discussed **more than 40% of the US-listed universe** at
least twice. Even if a 2021-era edge existed, a reader applying it today would be
using a screener that has roughly doubled in width since. This is a fact about
the sub, independent of anything above.
