"""Rate-limit-aware, resumable Arctic Shift backfill.

Replaces the torrent-based acquisition in design doc 4.1, which is unreachable
from this environment (see phase0/FEASIBILITY.md, Finding 1).

Two constraints shape this module:

  * Arctic Shift 403s if you parallelise and times out on windows that return
    too much at once. So: strictly serial, adaptive window, exponential backoff.
  * The container is ephemeral. So: append-only NDJSON plus a checkpoint file,
    re-run to resume. Never rewrites what it already has.

Usage:
    python3 arctic_shift_fetch.py posts    2010-01-01 2026-08-16 data/posts
    python3 arctic_shift_fetch.py comments 2019-01-01 2022-01-01 data/comments
"""

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://arctic-shift.photon-reddit.com/api"
SUB = "ValueInvesting"

# We deliberately do NOT pass `fields` and instead take the full object.
#
# The API's `fields` whitelist is narrower than the object it returns, and the
# mismatch is silent-ish: `permalink`, `is_self`, `domain`, `upvote_ratio` and
# `removed_by_category` are all present in responses but rejected with HTTP 400
# when requested. `removed_by_category` is the one that settles it - design doc
# 4.2 needs it to quantify the deleted/removed share, and it is unobtainable via
# field selection. Full objects run ~2-4 KB (posts) and ~1 KB (comments), which
# is affordable at this corpus size and keeps every downstream stage's options
# open.

PAGE = 100          # server max
MIN_WINDOW = 900    # 15 min - floor before we accept a lossy window
MAX_WINDOW = 86400 * 30
BASE_SLEEP = 1.6    # measured floor; below this we start drawing 403s


def _get(path, params, max_tries=7):
    """Serial GET with backoff. Returns (rows, soft_fail).

    soft_fail is True when the server asked us to slow down - the caller
    responds by shrinking the window rather than by retrying identically.
    """
    url = f"{BASE}/{path}?" + "&".join(f"{k}={v}" for k, v in params.items())
    for attempt in range(max_tries):
        try:
            # A custom UA is mandatory: Cloudflare rejects the default
            # "Python-urllib/3.x" signature with 403 "error code: 1010".
            req = urllib.request.Request(url, headers={"User-Agent": "value-screener-study/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read())
            if body.get("data") is not None:
                return body["data"], False
            # {"data": null, "error": "Timeout. Maybe slow down a bit"}
            if "timeout" in str(body.get("error", "")).lower():
                return None, True
            time.sleep(BASE_SLEEP * 2 ** attempt)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                # Caller error (e.g. an unselectable field name). Retrying just
                # burns minutes in silence - fail loudly instead.
                raise RuntimeError(f"bad request: {e.read()[:200]!r} for {url}") from e
            if e.code in (403, 429):          # rate limited - long cool-off
                time.sleep(min(90, 8 * 2 ** attempt))
            elif e.code == 422:
                # Ambiguous: usually "window too heavy", sometimes transient.
                # Retry a couple of times before telling the caller to shrink.
                if attempt < 2:
                    time.sleep(BASE_SLEEP * 2 ** attempt)
                    continue
                return None, True
            else:
                time.sleep(BASE_SLEEP * 2 ** attempt)
        except Exception:
            time.sleep(BASE_SLEEP * 2 ** attempt)
    return None, True


def fetch(kind, start, end, outdir):
    os.makedirs(outdir, exist_ok=True)
    ckpt_path = os.path.join(outdir, "_checkpoint.json")
    data_path = os.path.join(outdir, f"{kind}.ndjson")
    seen_path = os.path.join(outdir, "_seen.txt")

    cursor = start
    if os.path.exists(ckpt_path):
        saved = json.load(open(ckpt_path))
        cursor = dt.datetime.fromisoformat(saved["cursor"])
        print(f"resuming from {cursor}", file=sys.stderr)

    seen = set()
    if os.path.exists(seen_path):
        seen = set(open(seen_path).read().split())

    window = 86400 if kind == "posts" else 21600
    total = len(seen)

    out = open(data_path, "a")
    seen_f = open(seen_path, "a")

    while cursor < end:
        stop = min(cursor + dt.timedelta(seconds=window), end)
        rows, soft_fail = _get(
            f"{kind}/search",
            {
                "subreddit": SUB,
                "after": cursor.strftime("%Y-%m-%dT%H:%M:%S"),
                "before": stop.strftime("%Y-%m-%dT%H:%M:%S"),
                "limit": PAGE,
                "sort": "asc",
            },
        )

        if soft_fail:
            if window > MIN_WINDOW:
                window = max(MIN_WINDOW, window // 2)
                print(f"  shrink window -> {window}s", file=sys.stderr)
                time.sleep(BASE_SLEEP * 2)
                continue
            # already at the floor: record the hole rather than silently skipping
            print(f"  UNRECOVERABLE {cursor} .. {stop}", file=sys.stderr)
            with open(os.path.join(outdir, "_gaps.txt"), "a") as g:
                g.write(f"{cursor.isoformat()}\t{stop.isoformat()}\n")
            cursor = stop
            continue

        new = 0
        for row in rows:
            rid = row.get("id")
            if rid and rid not in seen:
                seen.add(rid)
                seen_f.write(rid + "\n")
                out.write(json.dumps(row, separators=(",", ":")) + "\n")
                new += 1
        total += new

        # A full page means the window was truncated. Rather than halving the
        # window and re-fetching what we already have, advance the cursor to
        # just after the last row we got and keep the window size. This turns
        # dense periods into O(rows/PAGE) requests instead of a bisection.
        if len(rows) >= PAGE:
            last = max(r["created_utc"] for r in rows)
            cursor = dt.datetime.utcfromtimestamp(last + 1)
            out.flush(); seen_f.flush()
            json.dump({"cursor": cursor.isoformat(), "total": total}, open(ckpt_path, "w"))
            print(f"  {cursor.date()} +{new} total={total} (paging)", file=sys.stderr)
            time.sleep(BASE_SLEEP)
            continue

        cursor = stop
        if window < MAX_WINDOW:
            window = min(MAX_WINDOW, int(window * 1.6))

        out.flush(); seen_f.flush()
        json.dump({"cursor": cursor.isoformat(), "total": total}, open(ckpt_path, "w"))
        print(f"  {cursor.date()} +{new} total={total} win={window}s", file=sys.stderr)
        time.sleep(BASE_SLEEP)

    out.close(); seen_f.close()
    print(f"DONE {kind}: {total} rows -> {data_path}")


if __name__ == "__main__":
    kind, start, end, outdir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    fetch(kind, dt.datetime.fromisoformat(start), dt.datetime.fromisoformat(end), outdir)
