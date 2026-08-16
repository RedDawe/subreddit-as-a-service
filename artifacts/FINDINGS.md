# Is r/ValueInvesting a useful stock screener?

**Short answer: not as a list of "what got mentioned". Possibly yes as a list of
"what got mentioned *most*".**

---

## Words used here

- **Cohort** — the year a stock was first discussed. We follow it forward 3 and
  5 years from there.
- **3-bagger** — the stock tripled (+200% or more), dividends included.
- **Wipeout** — the stock lost 70% or more, or went to roughly zero.
- **Control** — a stock the sub did *not* discuss, picked at random from those
  actually listed at the same time, and started on the same date.
- **Lift** — how much more often something happens in the sub's names than in
  the controls. Lift 2.0 = twice as often. **Lift 1.0 = no difference at all.**
- **Size-adjusted** — the sub talks about big companies, and big companies
  behave differently from small ones. So before comparing, we reweight the
  controls to have the same size mix as the sub's names. Otherwise you just
  measure "big companies did well", which we already knew.
- **Confidence interval** — the range the true answer plausibly sits in.
  **If the range includes 1.0, we cannot tell the sub apart from chance.**

Sample: 193 discussed stocks (4+ different people wrote about each, 2019–2021)
vs 196 controls.

---

## 1. Being mentioned means nothing

| outcome | sub | controls (size-adj) | lift | range |
|---|---|---|---|---|
| 3-bagger | 15.0% | 8.5% | 1.76 | 0.90 – 4.36 |
| beat the S&P | 35.2% | 42.4% | 0.83 | 0.57 – 1.57 |
| **wipeout** | **9.8%** | **4.8%** | **2.06** | **1.12 – 3.98** |

Both winner ranges include 1.0, so we can't distinguish the sub from chance on
finding winners. Beating the market: flat.

The one thing we *can* measure is that mentioned stocks were **twice as likely
to lose 70%+**. That range excludes 1.0.

**A caution about the raw numbers.** Unadjusted, the sub's stocks look *safer*
than controls (9.8% wipeouts vs 14.3%). That's pure size — the random controls
include small companies that fail often. Compare like with like and the sign
flips. This is why the size adjustment isn't optional.

---

## 2. But ranking them does something

Instead of "was it mentioned", ask "was it one of the most-discussed". Sorting
the same 193 stocks by how many different people wrote about them, 5-year:

| bucket | n | 3-baggers | **wipeouts** | median return |
|---|---|---|---|---|
| top 10 | 10 | 40.0% | **0%** | +145% |
| top 25 | 25 | 24.0% | **0%** | +87% |
| top 50 | 50 | 22.0% | 2% | +88% |
| everything else | 143 | 12.6% | **12.6%** | +44% |

Controls: 10.7% 3-baggers, 14.3% wipeouts, +29% median.

Sorting by upvotes instead of author count gives the same shape (top 10: 40%
3-baggers, 0% wipeouts, +158% median). Same at the 3-year horizon.

**Every wipeout is in the bottom of the ranking.** The top 25 by any of the four
ranking measures had none at all.

That reframes finding #1: the "twice as likely to blow up" result is *entirely*
the thinly-discussed tail. Stocks a dozen people wrote about did not blow up.

**How much to believe this.** The wipeout pattern is consistent across all four
ranking measures and both horizons, which is reassuring. The *winner* side is
not established — size-adjusted lift for the top 10 is 3.20 but the range runs
0.64 to 11.56, so it includes 1.0. With 10 stocks in a bucket you cannot expect
better. Treat "ranking avoids disasters" as the finding and "ranking finds
winners" as an untested hypothesis worth more data.

---

## 3. The sub shows up late

Of 181 stocks that had a 50%+ run, **77.9% were first discussed after the run
had already started** — median 225 days after the low.

Whatever the sub is doing, it isn't early.

---

## 4. It mentions losers slightly more than winners

Within the sample, 3-year:

    3-baggers the sub mentioned    40.0%
    wipeouts the sub mentioned     47.4%
    all stocks the sub mentioned   50.7%

If the sub had a nose for winners, the first number would be the highest. It's
the lowest.

---

## 5. Other results, briefly

- **Portfolio**: +3.8%/year above what the risk factors explain, but not
  statistically significant (t = 1.19). The portfolio carries a large
  *small-company* tilt and **no value tilt at all** — odd for a value forum.
  Much of the raw return is a size bet.
- **Novelty**: at most 53% of picks were outside the S&P 500, and that's an
  upper bound (our membership list is current-only, so it overstates novelty).
- **vs "just buy big liquid stocks"**: the sub wins slightly on 3-baggers
  (15.0% vs 10.8%) and loses badly on wipeouts (9.8% vs 2.7%).
- **The funnel keeps widening**: the sub discussed 1.3% of US-listed stocks in
  2019, 28.5% in 2021, **40.7% in 2025**. As a filter it is getting weaker every
  year — which is exactly why the ranking approach matters more than the
  membership one.

---

## 6. What I'd do next

1. **Test the ranking properly.** This is the promising result and it's the
   least-tested. It also works on recent years: you can rank 2025 names today
   even though you can't score their 5-year return yet. Concretely — take the
   top 25 by author count each month from 2019 on, and track that as a rolling
   list.
2. **Separate bullish from bearish mentions.** Everything above counts any
   mention. "Is X a value trap?" currently counts the same as "I'm buying X".
   Given #2, this could matter a lot.
3. **More data.** 193 stocks gives ranges like 0.90–4.36. The limit is the free
   data quota (500 symbols/month), not money.

## Honesty note

Every unfixed bias in this study points the same way — toward making the sub
look *better* than it is (details in `docs/BIAS_REGISTER.md`). So the "mentions
mean nothing" result is solid, and the wipeout result is if anything understated.
The ranking result is the one that could still go either way with more data.
