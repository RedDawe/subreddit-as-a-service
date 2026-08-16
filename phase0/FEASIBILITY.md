# Phase 0 — Environment feasibility probe

Probe date: 2026-08-16. Every claim below was executed, not assumed.

**Verdict: buildable, but not as specified.** One stage (§4.1 acquisition) needs a
different source that works better than the one in the doc. One stage (§4.4 price data)
cannot be done honestly here without a paid subscription, and it is the stage the doc
itself flags as determining "whether the answer is true."

---

## Environment

| Resource | Value |
|---|---|
| CPU / RAM / free disk | 4 cores / 15 GB / 30 GB |
| Python | 3.11.15; pandas 3.0.5, pyarrow, yfinance 1.6.0 install fine |
| Egress | HTTPS via agent proxy; ports 80/443 only |

Compute is not a constraint at this data scale.

---

## Finding 1 — BitTorrent is blocked, so §4.1's primary source is unreachable

    port 6969 (tracker)  BLOCKED
    UDP 53               BLOCKED
    ports 80 / 443       OPEN

The Academic Torrents entry exists (`ba05199...` = "Reddit comments/submissions 2005-06 to
2024-12") but its page serves only a `.torrent` file — no HTTP mirror, no webseed. The
Arctic Shift dump files listed in §4.1 as the gap-fill are distributed the same way.

**Both documented acquisition paths are torrent-only and therefore unavailable.**

## Finding 2 — the Arctic Shift REST API fully replaces them, and is strictly better

Not a workaround; a better fit for this project.

- Reaches back to **2010-09-29** — the subreddit's actual first post, so there is no
  historical gap to fill at all.
- Returns **full submission objects** (all fields: `selftext`, `author_fullname`,
  `permalink`, `link_flair_text`, `retrieved_on`, …), not a reduced view.
- Live through the probe date, so §4.1's separate "gap fill 2025-01 → present" step
  disappears — one source covers the whole span.
- Removes the zstd/NDJSON parsing stage (§4.1 `Watchful1/PushshiftDumps`) and the disk
  pressure entirely.

Endpoints verified: `/api/posts/search`, `/api/comments/search`, `/api/subreddits/search`.

## Finding 3 — §4.2's headline caveat is likely **wrong for this source** (good news)

The doc's first gate task assumes `score` is "captured shortly after post creation, often
frozen near zero," which would break the conviction measure. Measured on a real sample:

    retrieval lag: median 74.9 days (min 71.9, max 77.7, n=12)
    sample post:   score=15, num_comments=30   <- real values, not zeros

Scores were captured **~2.5 months after posting**, well past the point where a Reddit
thread's score has settled. The §4.2 gate task is still worth running at the specified
n=50 across years, but the prior should shift: an upvote-weighted conviction measure looks
salvageable, and the structural-proxy fallback may not be needed.

## Finding 4 — price data is the real blocker, and it is fatal as specified

§4.4 calls yfinance "unacceptable alone." Confirmed directly:

| Ticker | Rows 2019–2024 | Fate |
|---|---|---|
| AAPL | 1258 | listed |
| SIVB | **0** | bank failure, 2023 |
| BBBYQ | **0** | bankruptcy, 2023 |
| ATVI | **0** | **acquired by Microsoft, 2023** |

The ATVI row is the important one. It is not a bankruptcy — it is a *successful* exit at a
premium, and yfinance still returns nothing. So the survivorship damage is **two-sided**:
the backtest would silently drop both the wipeouts and a class of winners. That is worse
than the one-directional bias §8 anticipates, and it corrupts `winner_3x`, `wipeout`, and
the matched-control arm simultaneously.

Available here: no CRSP, no Sharadar/Norgate/Polygon credentials. Stooq is behind a
JS challenge. This is a **subscription/credential gap, not an environment limitation** —
the network path to those vendors is open (`data.nasdaq.com` returns 200). Supply a key
and this unblocks immediately.

## Finding 5 — entity resolution is servable for US names

SEC EDGAR `company_tickers.json` fetches fine (795 KB, needs a `User-Agent`), giving the
ticker→CIK map §4.4 requires for stable entity IDs. Note this is a **current-state**
snapshot, not point-in-time; the doc's ticker-reuse requirement (FB→META, recycled dead
tickers) needs EDGAR's historical former-names data layered on top.

## Finding 6 — rate limits make backfill a long, checkpointed job

- ~1.4–2.0 s per request when polite; **HTTP 403 if requests are parallelized**.
- `/api/comments/search` is much heavier: it **times out on 7-day windows**, and needs
  ~6–12 h windows (a 12 h window in Feb 2020 returned 3 comments and succeeded).
- Comments carry roughly 10–20× the volume of submissions and, per §10, most of the bear
  cases — so they are not optional.

Backfill is therefore a **multi-hour serial job**, and this container is reclaimed after
inactivity. Any real run must checkpoint to disk/git and resume, not run in one shot.

## Finding 7 — no API key for bulk stance classification

`ANTHROPIC_API_KEY` is unset (`/v1/models` → 401). §5.3 requires an LLM pass over every
mention span and explicitly rules out lexicon sentiment. Hand-labelling the 200-example
validation set is fine; classifying the full mention set at scale needs a supplied key.

---

## What this means for the phasing in §7

| Phase | Status here |
|---|---|
| 0 — Feasibility (A1, score check) | **Runnable now.** Score check partly pre-answered (Finding 3) |
| 1 — Extraction + hand-labelling | **Runnable now.** Pure text work, no external deps |
| 2 — Panel + returns | **Blocked** on price data (Finding 4); stance needs a key (Finding 7) |
| 3 — Analysis A2–A8 | Blocked behind Phase 2 |

The doc's own kill-gate logic is worth honouring: A1 (§6, "run first") is the cheapest
test, it is fully runnable here, and it can end the project before any paid data is bought.
The right order is A1 → extraction validation → *then* decide whether the price-data
subscription is justified — which is also what §10's last open question proposes.
