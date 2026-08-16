"""The §4.2 gate task: is the archived `score` trustworthy?

Design doc §4.2 assumes archived scores are "captured shortly after post
creation, often frozen near zero", which would break any upvote-weighted
conviction measure and force a fallback to structural proxies.

This script answers that in two ways:

  1. `lag` - always available. Every archived object carries `retrieved_on`;
     compared against `created_utc` this says how long after posting the score
     was frozen. A capture lag of days-to-months means the score had time to
     settle, and the §4.2 concern largely dissolves.

  2. `live` - needs Reddit OAuth (REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET; free,
     see docs/UNBLOCKING.md). Samples N old posts and compares archived score
     against today's score, reporting Spearman correlation. This is the check
     the design doc actually specifies.

The gate is on the *correlation*, not on absolute agreement: scores drift
upward over time, so archived and live values will not match. What matters for
a conviction measure is whether they rank names the same way.
"""

import argparse
import datetime as dt
import json
import os
import random
import statistics
import sys
import urllib.parse
import urllib.request


def lag_report(path, sample=None):
    lags, zero_scores, n = [], 0, 0
    rows = []
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            if d.get("retrieved_on") and d.get("created_utc"):
                rows.append(d)
    if sample and len(rows) > sample:
        rows = random.Random(20260816).sample(rows, sample)

    by_year = {}
    for d in rows:
        lag = (d["retrieved_on"] - d["created_utc"]) / 86400
        lags.append(lag)
        y = dt.datetime.utcfromtimestamp(d["created_utc"]).year
        by_year.setdefault(y, []).append(lag)
        if (d.get("score") or 0) <= 1:
            zero_scores += 1
        n += 1

    if not lags:
        print("no retrieved_on timestamps found")
        return

    print(f"documents with retrieval timestamps : {n:,}")
    print(f"capture lag (days)  median={statistics.median(lags):.1f}  "
          f"mean={statistics.mean(lags):.1f}  "
          f"min={min(lags):.2f}  max={max(lags):.1f}")
    print(f"share captured <24h of posting      : "
          f"{sum(1 for l in lags if l < 1) / n:.1%}")
    print(f"share with score <= 1               : {zero_scores / n:.1%}")

    print("\nby year:")
    print(f"  {'year':<6}{'n':>7}{'median lag (d)':>16}{'share <24h':>12}")
    for y in sorted(by_year):
        ls = by_year[y]
        print(f"  {y:<6}{len(ls):>7,}{statistics.median(ls):>16.1f}"
              f"{sum(1 for l in ls if l < 1) / len(ls):>12.1%}")

    med = statistics.median(lags)
    fast = sum(1 for l in lags if l < 1) / n
    low = zero_scores / n
    print()
    # A high share of score<=1 is the symptom §4.2 predicts, but it has two very
    # different causes. Captured-too-early means the number is an artifact and
    # unusable. Captured-late-and-still-1 means the post genuinely got no
    # traction - which is real signal, and exactly what a small sub looks like.
    # Reporting only the share would conflate the two.
    if low > 0.4:
        cause = "early capture (artifact)" if fast > 0.5 else \
                "genuinely low engagement (real signal)"
        print(f"NOTE: {low:.0%} of documents have score <= 1. Given the capture lag")
        print(f"  above, the likely cause is {cause}.")
        if fast <= 0.5:
            print("  These are settled scores on a small subreddit, not frozen ones.")
            print("  They still compress conviction: a measure that cannot separate")
            print("  names inside a mass of 1-point posts needs the §4.2 structural")
            print("  proxies as a companion, even though the scores are trustworthy.")
        print()
    if med < 1 or fast > 0.5:
        print("VERDICT: scores were captured close to posting time. Treat archived")
        print("  score as unreliable and fall back to the structural proxies in")
        print("  §4.2 (top-level vs buried, thread reply count, post length).")
    else:
        print("VERDICT: scores were captured well after posting, so they had time to")
        print("  settle. An upvote-weighted conviction measure looks defensible.")
        print("  Confirm with `--live` once Reddit credentials are available.")


def _reddit_token():
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        sys.exit("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set - see docs/UNBLOCKING.md")
    import base64
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": f"Basic {auth}", "User-Agent": "value-screener-study/0.1"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["access_token"]


def live_report(path, n=50, seed=20260816):
    token = _reddit_token()
    rows = [json.loads(l) for l in open(path)]
    rows = [d for d in rows if d.get("score") is not None]
    picked = random.Random(seed).sample(rows, min(n, len(rows)))

    import time
    pairs = []
    for i in range(0, len(picked), 100):
        chunk = picked[i:i + 100]
        ids = ",".join("t3_" + d["id"] for d in chunk)
        req = urllib.request.Request(
            f"https://oauth.reddit.com/api/info?id={ids}",
            headers={"Authorization": f"bearer {token}",
                     "User-Agent": "value-screener-study/0.1"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            live = json.loads(r.read())
        live_by_id = {c["data"]["id"]: c["data"] for c in live["data"]["children"]}
        for d in chunk:
            lv = live_by_id.get(d["id"])
            if lv:
                pairs.append((d["score"], lv.get("score"), d["id"]))
        time.sleep(1.2)

    if not pairs:
        print("no posts could be re-fetched (all deleted?)")
        return

    def spearman(xs, ys):
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            r = [0.0] * len(v)
            for pos, i in enumerate(order):
                r[i] = pos
            return r
        rx, ry = rank(xs), rank(ys)
        mx, my = statistics.mean(rx), statistics.mean(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
        return num / den if den else 0.0

    arch = [p[0] for p in pairs]
    live_s = [p[1] for p in pairs]
    rho = spearman(arch, live_s)
    print(f"re-fetched {len(pairs)} of {len(picked)} sampled posts")
    print(f"archived score  median={statistics.median(arch):.0f}")
    print(f"live score      median={statistics.median(live_s):.0f}")
    print(f"Spearman rho    = {rho:.3f}")
    print()
    if rho >= 0.7:
        print("VERDICT: archived scores rank names much like live scores do.")
        print("  Upvote-weighted conviction is usable.")
    else:
        print("VERDICT: weak rank agreement. Fall back to structural proxies (§4.2).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("docs")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--n", type=int, default=50)
    a = ap.parse_args()
    if a.live:
        live_report(a.docs, a.n)
    else:
        lag_report(a.docs)
