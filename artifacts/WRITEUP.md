# Is r/ValueInvesting a useful idea screener?

**Headline verdict (5-year horizon): NULL.**

Adjusted lift is 1.62x but the 95% interval [0.83, 4.20] spans 1.0, so the data cannot distinguish the subreddit from a size-matched draw. Per design doc 3.2 the honest conclusion is "just use a screener".

Read this alongside `docs/BIAS_REGISTER.md`. The residual bias points
toward flattering the subreddit, so a positive result is an upper bound
and a null result is robust.

## A2 - lift

Treated: 193 names with >=4 distinct authors, formation 2019-2021. Controls: 188 names drawn from the point-in-time listed universe.

| outcome | treated | control (raw) | control (size-adj) | naive lift | adjusted lift | 95% CI |
|---|---|---|---|---|---|---|
| `winner_3x` | 15.0% | 11.2% | 9.3% | 1.35 | **1.62** | [0.83, 4.20] |
| `outperformer` | 35.2% | 26.1% | 41.0% | 1.35 | **0.86** | [0.56, 1.83] |
| `wipeout` | 9.8% | 14.4% | 4.7% | 0.69 | **2.08** | [1.09, 3.94] |

Median forward return: treated +61.7% vs control +29.3%. Survived the full horizon: 94% vs 81%.

The gap between naive and adjusted lift is the size skew: the subreddit
talks about big liquid names, and those carry their own returns.

## A3 - recall, winners and losers

```
{
 "winner_3x": {
  "n": 50,
  "mentioned": 29,
  "recall": 0.58
 },
 "wipeout": {
  "n": 46,
  "mentioned": 19,
  "recall": 0.41304347826086957
 },
 "outperformer": {
  "n": 117,
  "mentioned": 68,
  "recall": 0.5811965811965812
 },
 "all names": {
  "n": 381,
  "mentioned": 193,
  "recall": 0.5065616797900262
 }
}
```
Read the GAP between winner recall and loser recall. If they are similar the sub has measured nothing but its own breadth (1.2).

## A8 - dose-response

```
{
 "3-4": {
  "n": 61,
  "winner_3x": 0.09836065573770492,
  "wipeout": 0.18032786885245902,
  "median_return": 0.414397
 },
 "5-9": {
  "n": 76,
  "winner_3x": 0.14473684210526316,
  "wipeout": 0.09210526315789473,
  "median_return": 0.5133845
 },
 "10-19": {
  "n": 35,
  "winner_3x": 0.17142857142857143,
  "wipeout": 0.02857142857142857,
  "median_return": 0.716491
 },
 "20+": {
  "n": 21,
  "winner_3x": 0.2857142857142857,
  "wipeout": 0.0,
  "median_return": 1.022342
 }
}
```
A flat curve suggests coincidental coverage rather than signal.

## A7 - portfolio

```
{
 "equal_weighted": 1.0277319170984456,
 "author_weighted": 1.863666456726987,
 "benchmark": 1.003702616580311,
 "excess": 0.024029300518134677
}
```
Unadjusted; see the factor alpha below.

## A4 - timing

```
{
 "n": 181,
 "share_after": 0.7790055248618785,
 "median_lag_days": 225
}
```

## A5 - novelty

```
{
 "share_top_quintile": 0.36787564766839376,
 "share_above_median": 0.7616580310880829,
 "sp500_confirmed_in": 0.47150259067357514,
 "novelty_upper_bound": 0.5284974093264249,
 "sp500_unknown": 0.48186528497409326
}
```

## A6 - vs a trivial screen

```
{
 "winner_3x": {
  "sub": 0.15025906735751296,
  "screen": 0.10810810810810811,
  "ratio": 1.3898963730569949
 },
 "outperformer": {
  "sub": 0.35233160621761656,
  "screen": 0.32432432432432434,
  "ratio": 1.086355785837651
 },
 "wipeout": {
  "sub": 0.09844559585492228,
  "screen": 0.02702702702702703,
  "ratio": 3.6424870466321244
 }
}
```

## A7 - factor-adjusted alpha

```
{
 "months": 87,
 "alpha_monthly": 0.003132052655395982,
 "alpha_annual": 0.03823888291842348,
 "t_stat": 1.1885667392514028,
 "betas": {
  "Mkt-RF": 0.954945863574187,
  "SMB": 0.6097678148687725,
  "HML": -0.1221321065576655,
  "RMW": 0.0013647489188727832,
  "CMA": 0.411930156471785,
  "Mom": -0.0948933098780633
 }
}
```

## What this does not establish

- Stance is not classified, so this is all-mentions, not bullish-only.
  Design doc 5.3 makes bullish-only the headline and this the robustness
  check; only the robustness check exists.
- Submissions only. Comments carry most of the volume and most of the
  bear cases (10).
- Sector is not controlled for - no free sector source. Size only.
- The extraction gate passed on 30 self-labelled documents, not 300
  independently labelled ones.
- Non-US listings are structurally invisible, so H3 is unanswered.

