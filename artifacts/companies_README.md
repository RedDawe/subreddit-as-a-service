# companies.csv — check the results yourself

One row per company per horizon (3-year and 5-year), 778 rows. Opens in Excel,
Sheets, pandas, whatever.

Half the rows are stocks r/ValueInvesting discussed; half are comparison stocks
it never mentioned, drawn at random from those actually listed at the time and
started on the same dates.

## Columns

| column | meaning |
|---|---|
| `ticker` | as traded at the time; may be delisted since |
| `group` | `mentioned` or `not_mentioned` (the comparison group) |
| `horizon_years` | 3 or 5 — the same stock appears at both |
| `n_mentions` | times mentioned in posts, 2019–2021 |
| `n_authors` | **different people** who mentioned it — the better measure |
| `total_upvotes` | summed score of the posts mentioning it |
| `best_post_upvotes` | score of the single best-received post |
| `rank_by_authors` | 1 = most-discussed. Blank for comparison stocks |
| `rank_by_upvotes` | same, ranked by upvotes |
| `entry_date` / `entry_price` | first mention, and the price then |
| `exit_date` / `exit_price` | horizon end — **or the last day it traded**, if it died or was acquired first |
| `forward_return_pct` | total return, dividends included |
| `benchmark_return_pct` | what SPY did over the identical window |
| `excess_vs_spy_pct` | the difference |
| `tripled` | 1 if it returned +200% or more |
| `beat_spy` | 1 if it beat SPY |
| `lost_70pct` | 1 if it lost 70% or more |
| `survived_full_horizon` | 0 = delisted, bankrupt or acquired before the horizon ended |
| `dollar_volume_at_entry` | price × volume — a proxy for company size |
| `size_rank_in_sample` | 1 = biggest of the 389 stocks here |

## Things worth trying

- Sort by `rank_by_authors` and look at `size_rank_in_sample` next to it. The
  most-discussed stocks are mostly the biggest ones — that's the finding that
  sank the "just follow the most-mentioned" idea.
- Filter `survived_full_horizon = 0`. These are the acquisitions and
  bankruptcies. They're **in** the data on purpose: most free stock data quietly
  drops them, which makes any backtest look far better than reality.
- Compare `forward_return_pct` against `benchmark_return_pct` per row. A stock
  can double and still lose to the index.
- Filter `group = not_mentioned` and sort by `dollar_volume_at_entry` to build
  "the 25 biggest stocks nobody here discussed" — the comparison that showed the
  sub's top picks weren't adding anything.

## Caveats that matter when reading it

- **2019–2021 first mentions only.** Newer picks have no 5-year result yet.
- **Only stocks 4+ different people wrote about.** This is the sub's
  high-conviction subset, not everything it ever mentioned.
- **No sentiment.** "Is X a value trap?" counts the same as "I'm buying X".
- **US-listed only**, and posts only — comments were used elsewhere but not for
  choosing these companies.
- Prices are dividend- and split-adjusted (Tiingo).
