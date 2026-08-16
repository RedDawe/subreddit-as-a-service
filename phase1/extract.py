"""Stage 2-3: candidate extraction and entity resolution (design doc 5.2).

Three channels, unioned then resolved to a CIK:

  1. cashtags      - $NVDA           high precision, low recall
  2. bare tickers  - NVDA            needs stoplist tiering + context evidence
  3. company names - "Berkshire"     carries most of the recall

Output rows: (doc_id, doc_type, created_utc, author, entity_id, ticker,
              channel, confidence, span_start, span_end, evidence)

Design note: rather than accept/reject bare tokens outright, each candidate
carries an evidence set, and the tier from stoplist.py sets how much evidence is
required. That keeps Allstate ("ALL") and KeyCorp ("KEY") reachable without
letting every "all" and "key" through, which is the precision/recall trade the
design doc calls the hard part.
"""

import json
import re
import sys

from stoplist import tier
from universe import MANUAL_ALIASES, build

# ---------------------------------------------------------------- text hygiene

CODE_BLOCK = re.compile(r"```.*?```|`[^`]*`", re.S)
URL = re.compile(r"https?://\S+|www\.\S+")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
QUOTE_LINE = re.compile(r"^\s*&gt;.*$|^\s*>.*$", re.M)


def clean(text):
    """Strip constructs that generate false tickers, preserving offsets loosely.

    Quoted lines are dropped: quoting another user's mention is not this
    author's mention, and counting it double-counts one opinion.
    """
    if not text:
        return ""
    text = CODE_BLOCK.sub(" ", text)
    text = MD_LINK.sub(r"\1", text)
    text = URL.sub(" ", text)
    text = QUOTE_LINE.sub(" ", text)
    return text


# ---------------------------------------------------------------- context cues

VALUATION_CUE = re.compile(
    r"\b(p/?e|p/?b|p/?s|ev/?ebitda?|dcf|fcf|roic|roe|margin|moat|earnings|"
    r"revenue|dividend|yield|buyback|book value|intrinsic|undervalued|overvalued|"
    r"valuation|market cap|mkt cap|share[s]?|stock|position|bought|buying|sold|"
    r"selling|holding|long|short|price target|balance sheet|cash flow|eps|"
    r"guidance|multiple|cheap|expensive|value trap|bagger|ticker)\b",
    re.I,
)
MONEY_CUE = re.compile(r"\$\s?\d|\d+\s?(x|%)|\b\d+\.\d+\b")
# "(NVDA)", "NVDA:", "NVDA -", i.e. syntax that flags a symbol as a symbol
SYMBOL_SYNTAX = re.compile(r"[(\[]([A-Z]{1,5})[)\]]|\b([A-Z]{2,5})\s*[:\-–]\s")

CASHTAG = re.compile(r"\$([A-Z]{1,5})(?:\.([A-Z]))?\b")
UPPER_TOKEN = re.compile(r"\b([A-Z]{1,5})(?:\.([A-Z]))?\b")

CONTEXT_RADIUS = 220


def _context(text, start, end):
    return text[max(0, start - CONTEXT_RADIUS): end + CONTEXT_RADIUS]


class Extractor:
    def __init__(self):
        self.by_ticker, self.name_aliases = build()
        self.name_aliases = dict(self.name_aliases)
        self.name_aliases.update(MANUAL_ALIASES)
        # Longest-first so "berkshire hathaway" wins over "berkshire".
        names = sorted(self.name_aliases, key=len, reverse=True)
        # Only alphabetic aliases of reasonable length are worth regexing.
        names = [n for n in names if len(n) >= 5 and n.replace(" ", "").isalpha()]
        self.name_re = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I
        )
        self.cik_to_ticker = {}
        for t, meta in self.by_ticker.items():
            self.cik_to_ticker.setdefault(meta["cik"], t)

    # Stripping corporate suffixes leaves a long tail of aliases that are just
    # ordinary English - "growth" (GSTK), "honest" (HNST), "thesis" (THSGF).
    # Matched case-insensitively these fire constantly on normal prose, so
    # single-word aliases inside common English get the proper-noun treatment:
    # they must appear Capitalised AND near valuation language.
    def _alias_needs_proof(self, alias):
        if " " in alias:
            return False
        if alias in MANUAL_ALIASES:
            return False
        from stoplist import _english_ranks
        return _english_ranks().get(alias) is not None

    # ------------------------------------------------------------- channels

    def _cashtags(self, text):
        for m in CASHTAG.finditer(text):
            sym = m.group(1) + (("-" + m.group(2)) if m.group(2) else "")
            meta = self.by_ticker.get(sym) or self.by_ticker.get(m.group(1))
            if meta:
                yield dict(ticker=sym, entity_id=meta["cik"], channel="cashtag",
                           confidence=0.97, span=(m.start(), m.end()),
                           evidence=["cashtag"])

    def _names(self, text):
        for m in self.name_re.finditer(text):
            surface = m.group(1)
            alias = surface.lower()
            cik = self.name_aliases.get(alias)
            if not cik:
                continue
            evidence = ["company_name"]
            conf = 0.90
            if self._alias_needs_proof(alias):
                if not surface[:1].isupper():
                    continue                       # "growth" is not Growth Corp
                if not VALUATION_CUE.search(_context(text, *m.span())):
                    continue
                evidence.append("capitalised+valuation")
                conf = 0.75
            yield dict(ticker=self.cik_to_ticker.get(cik, ""), entity_id=cik,
                       channel="name", confidence=conf,
                       span=m.span(), evidence=evidence)

    def _bare(self, text, doc_cashtags, doc_names):
        for m in UPPER_TOKEN.finditer(text):
            base = m.group(1)
            sym = base + (("-" + m.group(2)) if m.group(2) else "")
            meta = self.by_ticker.get(sym) or self.by_ticker.get(base)
            if not meta:
                continue
            if m.start() > 0 and text[m.start() - 1] == "$":
                continue                                  # already a cashtag

            t = tier(base)
            ctx = _context(text, *m.span())
            evidence = []
            if meta["cik"] in doc_names:
                evidence.append("name_in_doc")
            if base in doc_cashtags:
                evidence.append("cashtag_in_doc")
            if SYMBOL_SYNTAX.search(text[max(0, m.start() - 2): m.end() + 3]):
                evidence.append("symbol_syntax")
            if VALUATION_CUE.search(ctx):
                evidence.append("valuation_language")
            if MONEY_CUE.search(ctx):
                evidence.append("numeric_context")

            strong = {"name_in_doc", "cashtag_in_doc", "symbol_syntax"}
            has_strong = bool(strong & set(evidence))

            if t == "JARGON":
                if not has_strong:
                    continue
                conf = 0.80
            elif t == "COMMON":
                # Needs a strong cue, or both weak cues together.
                if not has_strong and len(evidence) < 2:
                    continue
                conf = 0.88 if has_strong else 0.72
            else:                                          # CLEAR
                if not evidence:
                    conf = 0.70          # plausible but uncorroborated
                else:
                    conf = 0.93 if has_strong else 0.85

            yield dict(ticker=sym, entity_id=meta["cik"], channel="bare",
                       confidence=conf, span=m.span(), evidence=evidence)

    # ------------------------------------------------------------- driver

    def extract(self, text):
        text = clean(text)
        if not text:
            return []
        doc_cashtags = {m.group(1) for m in CASHTAG.finditer(text)}
        doc_names = {c["entity_id"] for c in self._names(text)}

        hits = list(self._cashtags(text)) + list(self._names(text))
        hits += list(self._bare(text, doc_cashtags, doc_names))

        # Collapse overlapping hits on the same entity - "ON Semiconductor"
        # fires the name channel and the bare channel over nested spans, which
        # is one mention, not two. Keep the most confident, and merge evidence
        # so the surviving row records everything that corroborated it.
        hits.sort(key=lambda h: (h["entity_id"], h["span"][0], -h["confidence"]))
        merged = []
        for h in hits:
            prev = merged[-1] if merged else None
            if (prev and prev["entity_id"] == h["entity_id"]
                    and h["span"][0] < prev["span"][1]):
                prev["evidence"] = sorted(set(prev["evidence"]) | set(h["evidence"]))
                prev["confidence"] = max(prev["confidence"], h["confidence"])
                continue
            merged.append(dict(h))
        return sorted(merged, key=lambda h: h["span"])


def run(in_path, out_path, doc_type):
    ex = Extractor()
    n_docs = n_hits = 0
    with open(in_path) as f, open(out_path, "w") as out:
        for line in f:
            d = json.loads(line)
            text = (d.get("title", "") + "\n" + d.get("selftext", "")
                    if doc_type == "post" else d.get("body", ""))
            for h in ex.extract(text):
                out.write(json.dumps({
                    "doc_id": d["id"], "doc_type": doc_type,
                    "created_utc": d["created_utc"], "author": d.get("author"),
                    "link_id": d.get("link_id"), "score": d.get("score"),
                    "entity_id": h["entity_id"], "ticker": h["ticker"],
                    "channel": h["channel"], "confidence": round(h["confidence"], 3),
                    "span_start": h["span"][0], "span_end": h["span"][1],
                    "evidence": h["evidence"],
                }, separators=(",", ":")) + "\n")
                n_hits += 1
            n_docs += 1
    print(f"{doc_type}s: {n_docs} docs -> {n_hits} mentions")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
