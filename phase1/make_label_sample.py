"""Draw the hand-labelling sample for the design doc 5.2 validation gate.

The gate is precision >= 0.90 and recall >= 0.80 over 300 randomly sampled
documents, with both numbers reported in the writeup.

Two things this does deliberately:

  * Samples documents, not extractions. Sampling extractions can only ever
    measure precision - you would never see the mentions the extractor missed,
    and recall would be unmeasurable.
  * Stratifies by cohort year. The sub's language changed a lot between 2013 and
    2024; a uniform draw would be dominated by the recent, high-volume years and
    would hide extraction decay on older text.

Emits a TSV the labeller fills in by hand. Deliberately not JSON: this is meant
to be opened in a spreadsheet on whatever device is available.
"""

import argparse
import collections
import datetime as dt
import json
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docs")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20260816)
    ap.add_argument("--doc-type", default="post")
    args = ap.parse_args()

    by_year = collections.defaultdict(list)
    with open(args.docs) as f:
        for line in f:
            d = json.loads(line)
            text = ((d.get("title") or "") + "\n" + (d.get("selftext") or "")
                    if args.doc_type == "post" else (d.get("body") or ""))
            text = text.strip()
            if len(text) < 40:            # nothing to label
                continue
            y = dt.datetime.utcfromtimestamp(d["created_utc"]).year
            by_year[y].append((d["id"], y, text))

    rng = random.Random(args.seed)
    years = sorted(by_year)
    # Proportional-with-a-floor: every year that exists gets some representation,
    # so extraction quality can be checked across eras rather than only where the
    # volume is.
    total = sum(len(v) for v in by_year.values())
    quota = {}
    floor = max(5, args.n // (len(years) * 3)) if years else 0
    for y in years:
        quota[y] = max(floor, round(args.n * len(by_year[y]) / total))

    picked = []
    for y in years:
        pool = by_year[y]
        picked += rng.sample(pool, min(quota[y], len(pool)))
    rng.shuffle(picked)
    picked = picked[: args.n]

    with open(args.out, "w") as out:
        out.write("doc_id\tyear\tgold_tickers\tnotes\ttext\n")
        for doc_id, y, text in picked:
            flat = text.replace("\t", " ").replace("\r", " ").replace("\n", " ⏎ ")
            if len(flat) > 4000:
                flat = flat[:4000] + " …[truncated]"
            out.write(f"{doc_id}\t{y}\t\t\t{flat}\n")

    print(f"wrote {len(picked)} docs to {args.out}")
    print(f"year spread: {dict(collections.Counter(y for _, y, _ in picked))}")
    print("\nFill in `gold_tickers` as a comma-separated list of tickers a careful")
    print("reader would say the document is about (empty = none). Then run:")
    print(f"  python3 phase1/score_labels.py {args.out} <mentions.ndjson>")


if __name__ == "__main__":
    main()
