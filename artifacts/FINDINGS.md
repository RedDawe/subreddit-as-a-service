# Is r/ValueInvesting a useful stock screener?

**Short answer: no.** Being mentioned tells you nothing. Being mentioned *most*
sorts the sub's own names usefully, but gets you no further than "buy the 25
biggest US stocks" — which you can do without reading anything.

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

## 2. Ranking sorts the names — but so does market cap

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

### …but you could have got the same result without reading the sub

The obvious objection: the most-discussed stocks are mostly the biggest stocks,
and big US stocks did well over this period. So is the ranking adding anything?

Tested directly — the sub's top 25 against simply buying the 25 largest stocks:

| 5-year portfolio | 3-baggers | wipeouts | beat S&P | median |
|---|---|---|---|---|
| sub's top 25 | 24.0% | 0% | 44.0% | +87% |
| the 25 biggest | 24.0% | 12% | 44.0% | +98% |
| the 25 biggest the sub *never* discussed | 16.0% | 0% | 44.0% | **+102%** |

**Identical.** Same 3-bagger rate, same beat-the-market rate, and the biggest
stocks the sub never mentioned actually returned *more*. The 3-year table is the
same story with noisier numbers.

Even the "no wipeouts" result doesn't survive: the 25 biggest stocks the sub
never discussed also had zero wipeouts. Avoiding disasters is a **size** effect,
not a subreddit effect. You get it by buying big companies, whether or not
anyone on Reddit mentioned them.

The top 25 is not *purely* the biggest — 5 of them sit outside the top 100 by
size (GME, TME, DD, MMM, TGT) — but the median one ranks 26th, and the overlap
is enough that the ranking adds nothing measurable on top of "buy large caps".

**So: ranking sorts the sub's own names usefully, but it does not beat a screen
you could run in ten seconds without reading anything.** With 25 stocks per
bucket these numbers are noisy, so this isn't proof of no effect — but there is
no evidence of one.

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

1. **Find a ranking that isn't just market cap.** Plain popularity tracks size
   too closely to add anything. The interesting version is a ranking of what the
   sub discusses *relative to* how big the company is — a name 10 people wrote
   about that is 400th by size is a genuine signal; the same attention on Apple
   is not. That is testable with the data already here.
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
