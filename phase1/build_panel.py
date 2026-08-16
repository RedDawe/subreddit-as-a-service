"""Stage 5: the mention panel (design doc 5.4) - one row per (entity, month).

This is the canonical intermediate artifact and deliverable #1. Everything
downstream is a join against it, so it is built to be useful even if the study
itself is never finished.

Columns follow 5.4. Two deviations, both deliberate:

  * `total_score` / `max_score` are emitted but carry a companion column
    `score_lag_days_median`, because whether the score is trustworthy depends
    entirely on how long after posting it was captured (4.2). Measured on this
    corpus the lag is ~75 days, which is well past settling - but the number
    travels with the data so a reader can re-judge rather than take it on faith.
  * `n_removed` is added. 4.2 flags deleted/removed content as a survivorship
    bias that flatters the sub; it cannot be quantified later if it is not
    counted here.

Stance columns (n_bullish/n_bearish/n_neutral) are present but left null unless
a stance file is supplied - see phase2/. Nulls are honest; zeros would look like
measured neutrality.
"""

import argparse
import collections
import csv
import datetime as dt
import json
import statistics


def month_of(ts):
    d = dt.datetime.utcfromtimestamp(ts)
    return f"{d.year:04d}-{d.month:02d}"


def build(mentions_path, docs_paths, out_path, min_conf, stance_path=None):
    # doc_id -> metadata needed for the engagement/removal proxies
    doc_meta = {}
    for p, kind in docs_paths:
        with open(p) as f:
            for line in f:
                d = json.loads(line)
                doc_meta[d["id"]] = {
                    "kind": kind,
                    "score": d.get("score"),
                    "num_comments": d.get("num_comments"),
                    "retrieved_on": d.get("retrieved_on"),
                    "created_utc": d.get("created_utc"),
                    "removed": bool(d.get("removed_by_category"))
                    or (d.get("selftext") in ("[deleted]", "[removed]"))
                    or (d.get("body") in ("[deleted]", "[removed]")),
                    "author": d.get("author"),
                }

    stance = {}
    if stance_path:
        with open(stance_path) as f:
            for line in f:
                s = json.loads(line)
                stance[(s["doc_id"], s["entity_id"])] = s["stance"]

    cells = collections.defaultdict(lambda: {
        "n_mentions": 0, "authors": set(), "n_toplevel_posts": 0,
        "scores": [], "thread_comments": 0, "n_removed": 0,
        "lags": [], "tickers": collections.Counter(),
        "bullish": 0, "bearish": 0, "neutral": 0, "question": 0,
        "channels": collections.Counter(), "docs": set(),
    })
    first_seen = {}

    with open(mentions_path) as f:
        for line in f:
            m = json.loads(line)
            if m["confidence"] < min_conf:
                continue
            key = (m["entity_id"], month_of(m["created_utc"]))
            c = cells[key]
            meta = doc_meta.get(m["doc_id"], {})

            c["n_mentions"] += 1
            if m.get("author") and m["author"] != "[deleted]":
                c["authors"].add(m["author"])
            if meta.get("kind") == "post":
                c["n_toplevel_posts"] += 1
                if meta.get("num_comments") is not None:
                    # count each thread once, not once per mention in it
                    if m["doc_id"] not in c["docs"]:
                        c["thread_comments"] += meta["num_comments"] or 0
            if meta.get("score") is not None:
                c["scores"].append(meta["score"])
            if meta.get("removed"):
                c["n_removed"] += 1
            if meta.get("retrieved_on") and meta.get("created_utc"):
                c["lags"].append((meta["retrieved_on"] - meta["created_utc"]) / 86400)
            c["tickers"][m["ticker"]] += 1
            c["channels"][m["channel"]] += 1
            c["docs"].add(m["doc_id"])

            st = stance.get((m["doc_id"], m["entity_id"]))
            if st in ("bullish", "bearish", "neutral", "question"):
                c[st if st != "neutral" else "neutral"] += 1

            e = m["entity_id"]
            if e not in first_seen or m["created_utc"] < first_seen[e]:
                first_seen[e] = m["created_utc"]

    cols = ["entity_id", "ticker_at_date", "year_month", "n_mentions",
            "n_distinct_authors", "n_toplevel_posts", "n_bullish", "n_bearish",
            "n_neutral", "n_question", "total_score", "max_score",
            "score_lag_days_median", "total_thread_comments", "n_removed",
            "first_mention_ever", "months_since_first_mention",
            "n_cashtag", "n_bare", "n_name"]

    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for (entity, ym), c in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            fm = dt.datetime.utcfromtimestamp(first_seen[entity])
            y, mo = int(ym[:4]), int(ym[5:])
            months_since = (y - fm.year) * 12 + (mo - fm.month)
            has_stance = bool(stance)
            w.writerow([
                entity,
                c["tickers"].most_common(1)[0][0] if c["tickers"] else "",
                ym,
                c["n_mentions"],
                len(c["authors"]),
                c["n_toplevel_posts"],
                c["bullish"] if has_stance else "",
                c["bearish"] if has_stance else "",
                c["neutral"] if has_stance else "",
                c["question"] if has_stance else "",
                sum(c["scores"]) if c["scores"] else "",
                max(c["scores"]) if c["scores"] else "",
                round(statistics.median(c["lags"]), 1) if c["lags"] else "",
                c["thread_comments"],
                c["n_removed"],
                int(months_since == 0),
                months_since,
                c["channels"]["cashtag"], c["channels"]["bare"], c["channels"]["name"],
            ])
    print(f"panel rows: {len(cells)}  ->  {out_path}")
    if not stance:
        print("NOTE: stance columns left empty - no stance file supplied (5.3).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mentions")
    ap.add_argument("out")
    ap.add_argument("--posts")
    ap.add_argument("--comments")
    ap.add_argument("--stance")
    ap.add_argument("--min-conf", type=float, default=0.70)
    a = ap.parse_args()
    docs = [(p, k) for p, k in ((a.posts, "post"), (a.comments, "comment")) if p]
    build(a.mentions, docs, a.out, a.min_conf, a.stance)
