"""Stage 4: stance classification (design doc 5.3).

"A mention is not a recommendation." A large share of the sub is "is X a value
trap?", "talk me out of X", or an explicit bear case, so counting mentions as
buys biases H1 in an unknown direction.

The doc requires an LLM pass with the mention span highlighted, and explicitly
rules out lexicon sentiment (VADER et al.) as insufficient for financial text.
This module provides:

  * the prompt and batching harness for that LLM pass (needs ANTHROPIC_API_KEY,
    which is NOT set in this environment - see FEASIBILITY.md Finding 7);
  * a deliberately weak keyword baseline, used ONLY as a floor to compare the
    LLM against when the confusion matrix is reported. It is not a substitute,
    and `classify_all` refuses to write a stance file from it unless explicitly
    forced, so a rushed run cannot silently produce lexicon-quality labels and
    pass them off as the real thing.
"""

import argparse
import json
import os
import sys

LABELS = ("bullish", "bearish", "neutral", "question")

PROMPT = """You are labelling stance in r/ValueInvesting posts for a research study.

Below is a document with one company mention marked by «». Classify the AUTHOR'S
OWN stance toward that company, as expressed in this document.

Labels:
- bullish: the author thinks it is attractive / is buying / holds it favourably
- bearish: the author thinks it is unattractive, overvalued, or a value trap
- neutral: discussed without a directional view (news, comparison, definition)
- question: the author is asking others for a view rather than giving one

Rules:
- Label the author's stance, not the company's prospects.
- "Talk me out of X" is a question, not bullish.
- Quoting someone else's view is neutral unless the author endorses it.
- If the author is bullish on the sector but not this company, use neutral.

Return only a JSON object: {{"stance": "<label>", "confidence": <0-1>}}

Document:
---
{doc}
---
Mention: «{ticker}»"""


def mark_span(text, start, end, width=1500):
    """Return the document trimmed around the mention, with the span marked."""
    a = max(0, start - width)
    b = min(len(text), end + width)
    return (("…" if a else "") + text[a:start] + "«" + text[start:end] + "»"
            + text[end:b] + ("…" if b < len(text) else ""))


# --------------------------------------------------------------- weak baseline

BULL = ("undervalued", "cheap", "buying", "bought", "long ", "accumulating",
        "great business", "wide moat", "compounder", "bargain", "margin of safety",
        "load up", "conviction", "adding to")
BEAR = ("overvalued", "value trap", "avoid", "selling", "sold", "short ",
        "bagholder", "dying", "declining", "melting ice", "expensive", "bubble",
        "red flag", "accounting fraud")
QUES = ("?", "thoughts on", "am i missing", "talk me out", "what do you think",
        "any thoughts", "opinions on")


def baseline(text):
    t = text.lower()
    b = sum(t.count(k) for k in BULL)
    r = sum(t.count(k) for k in BEAR)
    q = sum(t.count(k) for k in QUES)
    if q and q >= max(b, r):
        return "question", 0.35
    if b > r:
        return "bullish", 0.35
    if r > b:
        return "bearish", 0.35
    return "neutral", 0.30


# ------------------------------------------------------------------- LLM pass

def llm_classify(docs, model="claude-sonnet-5"):
    """Classify via the Anthropic API. Requires ANTHROPIC_API_KEY."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Design doc 5.3 requires an LLM pass; "
            "lexicon sentiment is explicitly insufficient. Set the key (see "
            "docs/UNBLOCKING.md) or run with --baseline --force to produce "
            "clearly-labelled floor-quality output."
        )
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    out = []
    for d in docs:
        msg = client.messages.create(
            model=model, max_tokens=64,
            messages=[{"role": "user",
                       "content": PROMPT.format(doc=d["marked"], ticker=d["ticker"])}],
        )
        raw = msg.content[0].text.strip()
        try:
            parsed = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            stance = parsed.get("stance", "neutral")
            conf = float(parsed.get("confidence", 0.5))
        except Exception:                                    # noqa: BLE001
            stance, conf = "neutral", 0.0
        out.append((stance if stance in LABELS else "neutral", conf))
    return out


def classify_all(mentions_path, docs_path, out_path, doc_type,
                 use_baseline=False, force=False, limit=None):
    if use_baseline and not force:
        sys.exit("refusing to write lexicon-quality stance labels without --force "
                 "(5.3: lexicon sentiment performs poorly on financial text)")

    bodies = {}
    with open(docs_path) as f:
        for line in f:
            d = json.loads(line)
            bodies[d["id"]] = ((d.get("title") or "") + "\n" + (d.get("selftext") or "")
                               if doc_type == "post" else (d.get("body") or ""))

    items = []
    with open(mentions_path) as f:
        for line in f:
            m = json.loads(line)
            text = bodies.get(m["doc_id"])
            if not text:
                continue
            items.append({**m, "marked": mark_span(text, m["span_start"], m["span_end"]),
                          "text": text})
            if limit and len(items) >= limit:
                break

    if use_baseline:
        results = [baseline(i["text"]) for i in items]
        method = "keyword-baseline"
    else:
        results = llm_classify(items)
        method = "llm"

    with open(out_path, "w") as out:
        for i, (stance, conf) in zip(items, results):
            out.write(json.dumps({
                "doc_id": i["doc_id"], "entity_id": i["entity_id"],
                "ticker": i["ticker"], "stance": stance,
                "stance_confidence": round(conf, 3), "method": method,
            }, separators=(",", ":")) + "\n")
    print(f"{len(items)} mentions classified via {method} -> {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mentions")
    ap.add_argument("docs")
    ap.add_argument("out")
    ap.add_argument("--doc-type", default="post")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    classify_all(a.mentions, a.docs, a.out, a.doc_type, a.baseline, a.force, a.limit)
