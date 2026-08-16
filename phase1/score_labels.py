"""Score extraction against hand labels - the design doc 5.2 gate.

Reports precision, recall and F1 at the document level (did we find the tickers
a careful reader says the document is about), plus a per-channel and per-tier
breakdown so a failure points at what to fix rather than just failing.

Gate: precision >= 0.90 AND recall >= 0.80.
"""

import argparse
import collections
import csv
import json
import sys


def load_gold(path):
    gold = {}
    with open(path) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            raw = (row.get("gold_tickers") or "").strip()
            if raw == "" and (row.get("notes") or "").strip() == "":
                continue                      # unlabelled - excluded from scoring
            tickers = {t.strip().upper() for t in raw.split(",") if t.strip()}
            gold[row["doc_id"]] = tickers
    return gold


def load_pred(path, doc_ids, min_conf):
    pred = collections.defaultdict(set)
    meta = collections.defaultdict(list)
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r["doc_id"] in doc_ids and r["confidence"] >= min_conf:
                pred[r["doc_id"]].add(r["ticker"].upper())
                meta[r["doc_id"]].append(r)
    return pred, meta


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("mentions")
    ap.add_argument("--min-conf", type=float, default=0.0)
    args = ap.parse_args()

    gold = load_gold(args.labels)
    if not gold:
        sys.exit("no labelled rows found - fill in the gold_tickers column first")
    pred, meta = load_pred(args.mentions, set(gold), args.min_conf)

    tp = fp = fn = 0
    fp_examples, fn_examples = [], []
    by_channel = collections.Counter()
    for doc_id, g in gold.items():
        p = pred.get(doc_id, set())
        tp += len(g & p)
        for t in p - g:
            fp += 1
            src = next((m for m in meta[doc_id] if m["ticker"].upper() == t), {})
            fp_examples.append((doc_id, t, src.get("channel"), src.get("evidence")))
            by_channel[("FP", src.get("channel"))] += 1
        for t in g - p:
            fn += 1
            fn_examples.append((doc_id, t))
        for t in g & p:
            src = next((m for m in meta[doc_id] if m["ticker"].upper() == t), {})
            by_channel[("TP", src.get("channel"))] += 1

    p, r, f1 = prf(tp, fp, fn)
    print(f"labelled docs : {len(gold)}")
    print(f"min confidence: {args.min_conf}")
    print(f"TP={tp}  FP={fp}  FN={fn}")
    print(f"precision = {p:.3f}   (gate >= 0.90)")
    print(f"recall    = {r:.3f}   (gate >= 0.80)")
    print(f"F1        = {f1:.3f}")

    print("\nby channel:")
    channels = {c for _, c in by_channel}
    for c in sorted(channels, key=str):
        t_, f_ = by_channel[("TP", c)], by_channel[("FP", c)]
        prec = t_ / (t_ + f_) if t_ + f_ else 0.0
        print(f"  {str(c):10} TP={t_:<5} FP={f_:<5} precision={prec:.3f}")

    if fp_examples:
        print("\nfalse positives (first 15):")
        for e in fp_examples[:15]:
            print(f"  {e[0]}  {e[1]:6} via {e[2]} {e[3]}")
    if fn_examples:
        print("\nfalse negatives (first 15):")
        for e in fn_examples[:15]:
            print(f"  {e[0]}  {e[1]}")

    ok = p >= 0.90 and r >= 0.80
    print(f"\nGATE: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  Do not proceed to Phase 2 - an extraction stage with unmeasured")
        print("  or failing error rates invalidates everything downstream (5.2).")


if __name__ == "__main__":
    main()
