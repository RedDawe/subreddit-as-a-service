# Unblocking this study from a phone

Two things block Phase 2. Both are credential gaps, not environment limits —
every vendor endpoint below was probed from this container and is reachable; it
just returns 401/403 without a key.

| Endpoint | Probe result | Meaning |
|---|---|---|
| `data.nasdaq.com` (Sharadar SEP) | 403 | reachable, needs key |
| `api.polygon.io` | 401 | reachable, needs key |
| `eodhd.com` | 404 | reachable |
| `api.tiingo.com` | 200 | reachable |
| `api.anthropic.com` | 401 | reachable, needs key |
| `drive.google.com` | 302 | reachable |

---

## How to hand over a key — do NOT paste it in chat

Claude Code web environments carry their own environment variables, editable
from mobile Safari. That is the right channel: the value lands in the container
as an env var, never in the conversation transcript, and it survives container
restarts (this container is ephemeral and is reclaimed after inactivity).

1. Open **claude.ai/code** in Safari.
2. Go to the environment this session runs in → **Environment variables**.
3. Add the variable, save, and start a new session (or tell me to re-run — the
   variable is read at process start).

Docs: https://code.claude.com/docs/en/claude-code-on-the-web

Variables this repo reads:

| Variable | Unblocks | Read by |
|---|---|---|
| `NASDAQ_DATA_LINK_API_KEY` | price data / all of Phase 2–3 | `phase2/prices.py` |
| `ANTHROPIC_API_KEY` | stance classification (5.3) | `phase2/stance.py` |
| `SEC_UA` | optional; SEC asks for a contact string | `phase1/universe.py` |

**Do not** commit a key to the repo or paste it into chat. If one is ever
exposed, rotate it at the vendor rather than deleting the message.

---

## Blocker 1 — price data (the one that decides whether the answer is true)

Design doc §4.4 requires point-in-time universe membership, delisting returns,
total return, and corporate-action adjustment. Measured here, the free path
fails in a specific and nasty way:

    AAPL   1258 rows
    FRCB   1258 rows   $85.07 -> $0.04   (correctly priced!)
    SIVB      0 rows
    BBBYQ     0 rows
    ATVI      0 rows   (acquired at a premium, not bankrupt)
    TWTR      0 rows

Note this is **not** "yfinance drops delisted names". It drops them
*unpredictably* — First Republic is priced all the way down to four cents, while
SVB, Bed Bath, Activision and Twitter vanish entirely. Unpredictable missingness
is worse than uniform missingness: you cannot model it, so you cannot correct for
it, and it hits the winner tail (acquisitions) as well as the wipeout tail.

`phase2/prices.py` enforces this as the §7 Phase 2 gate — it refuses to compute
returns from a source that fails, rather than producing a beautiful wrong number.

### What to buy, from a phone

All of these are web signups that work fine in Safari. Ranked for this study:

1. **Sharadar SEP + TICKERS** via Nasdaq Data Link — closest to the doc's
   "Good paid" recommendation, US-only, delisted names retained, and an adapter
   is already written (`phase2/prices.py:Sharadar`). Best first choice.
2. **Polygon.io** — has delisted tickers; flat files on higher tiers. Needs a new
   adapter (~30 lines against the existing interface).
3. **EODHD** — cheaper, includes non-US, which matters for A5/H3.

Check current pricing on the vendor's own site; I have not verified prices and
they change.

**Do not** buy non-US coverage yet. Design doc §10 says to run A5 on a cheap
US-only pass first and only then decide whether non-US volume justifies the cost.
That is still the right order.

### If you have university access

CRSP is the academic standard and the doc's first choice, mainly because it has
proper delisting returns. If any affiliation gives you access, it beats all of
the above and costs nothing.

---

## Blocker 2 — stance classification

§5.3 needs an LLM pass over each mention with the span highlighted, and rules
out lexicon sentiment. Get a key at **console.anthropic.com** (works in Safari),
then set `ANTHROPIC_API_KEY` as above.

Cost is modest: the classifier sends a ~1.5k-character window per mention, not
whole threads, and only mentions above the confidence floor are sent.

Until then `phase2/stance.py` will not silently produce lexicon-quality labels —
it requires `--baseline --force` and stamps `method` into every row.

---

## What Google Drive is and isn't good for

**Good:** moving a file *you already have* into the container. A public or
link-shared Drive file can be pulled with a direct download URL, and
`drive.google.com` is reachable (302). So if you obtain a price CSV on another
machine, Drive is a fine transport.

**Not good:** as a substitute for the subscription. The blocker is not "we have
the data and can't move it" — it is that delisting-inclusive data has to be
bought or licensed in the first place.

**Never** put an API key in Drive and point me at it. Use the environment
variable channel instead.

---

## The Oracle VM

Not needed, and not worth digging out the SSH key for.

The one thing a long-lived VM would genuinely help with is the comments
backfill: Arctic Shift rate-limits to roughly one request every 1.6s, the
comments endpoint needs narrow windows, and comments run ~10–20× the volume of
submissions — so that job is measured in hours and this container is reclaimed
after inactivity. But the fetcher is checkpointed and resumable (`_checkpoint.json`
plus a `_seen.txt` dedupe set), so it can simply be resumed across sessions here.
Keep the VM as the backup it is.

---

## Fastest path to a real answer

1. Set `NASDAQ_DATA_LINK_API_KEY` from your phone (5 minutes).
2. I run `python3 phase2/prices.py sharadar` — the gate either passes or names
   exactly what is still missing.
3. Phase 2 and 3 then run end-to-end.

Phase 0 and Phase 1 need nothing from you and are running now.
