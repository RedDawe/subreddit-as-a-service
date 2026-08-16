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

from stoplist import SINGLE_LETTERS, tier
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
# "PS - I know that MSFT is not a value company" matched the dash form and
# emitted Pluralsight. These prose markers are never tickers in that position.
PROSE_MARKERS = {"PS", "PPS", "NB", "FYI", "EDIT", "TLDR", "TL", "IMO", "IMHO",
                 "BTW", "AKA", "ETA", "PSA", "UPDATE", "NOTE", "SOURCE", "RE"}

WORD = re.compile(r"[A-Za-z0-9&]+")
CASHTAG = re.compile(r"\$([A-Z]{1,5})(?:\.([A-Z]))?\b")
UPPER_TOKEN = re.compile(r"\b([A-Z]{1,5})(?:\.([A-Z]))?\b")

CONTEXT_RADIUS = 220

# Data providers, brokers and financial media are listed companies AND the
# things this sub constantly cites as sources. "Morningstar says X is
# undervalued" is a citation of a research vendor, not a thesis about owning
# Morningstar - but the entity resolves correctly either way, so no amount of
# ticker-matching catches it. Left unhandled, MORN alone contributed 698
# mentions, which would place it in the top ten names and distort every
# per-name statistic downstream.
#
# These names ARE genuinely discussed as investments too (people do own SCHW,
# SPGI, V), so a blocklist would be wrong. Instead the mention is demoted only
# when it sits in a citation construction.
# Deliberately narrow. Generic prepositions and verbs ("on", "from", "has")
# fire on ordinary theses - "DD on AutoNation (AN)" and "Morningstar has a wide
# moat" are both real discussions and must NOT be demoted - so only
# unambiguously citational constructions qualify.
CITATION_PATTERN = re.compile(
    r"\b(according to|as per|sourced? from|data from|screenshot from|"
    r"pulled from|via|courtesy of)\s*$",
    re.I,
)
CITATION_TRAILING = re.compile(
    r"^\s*(says?|said|shows?|showed|reports? that|rates? it|estimates?|"
    r"screener|terminal|fair value estimate|premium|paywall|"
    r"\.com|\.co\.uk)\b",
    re.I,
)


def _context(text, start, end):
    return text[max(0, start - CONTEXT_RADIUS): end + CONTEXT_RADIUS]


# Companies whose role in THIS sub's discourse is overwhelmingly "tool I used"
# rather than "stock I am considering": research vendors, index providers and
# exchanges. Sampling 656 surviving Morningstar mentions found essentially all
# of them to be tool references - "Morningstar Price/Fair Value: 0.64",
# "Gold-rated by Morningstar", "fair value estimation from Morningstar" - in
# constructions too varied for a citation-phrase list to catch.
#
# So for these names only, the burden of proof is inverted: a bare surface
# mention is assumed to be a citation, and INVESTMENT framing must be shown.
# Everything else in the universe keeps the normal rule. This is a heuristic
# standing in for the role/stance judgement design doc 5.3 defers to an LLM
# pass, and it is deliberately narrow.
VENDOR_ROLE_TICKERS = {
    "MORN",   # Morningstar - research/fair-value data
    "FDS",    # FactSet
    "MSCI",   # index provider
    "SPGI",   # S&P Global - ratings/indices
    "MCO",    # Moody's - ratings
    "NDAQ",   # Nasdaq - the exchange
    "ICE",    # ICE/NYSE - the exchange
    "TRI",    # Thomson Reuters
    "LSEGY",  # London Stock Exchange Group - "listed on the London Stock
              # Exchange" is a venue reference, not a thesis about LSEG
    "CBOE",   # Cboe - likewise, usually the venue
}
INVESTMENT_FRAMING = re.compile(
    r"\b(long|short|own|owning|bought|buying|sell|selling|sold|position|"
    r"shares?|stock|valuation|undervalued|overvalued|moat|p/?e|market cap|"
    r"revenue|earnings|margin|dividend|buyback|holding|portfolio)\b",
    re.I,
)
VENDOR_FRAMING_RADIUS = 60

# Fund-family brand words resolve to whichever ETF ticker happens to carry the
# brand in its registered name ("iShares" -> IAU), so a sentence about an
# iShares EV fund emits a gold-trust mention. These are never company mentions.
ETF_BRAND_ALIASES = {
    "ishares", "vanguard", "spdr", "invesco", "wisdomtree", "proshares",
    "direxion", "globalx", "global x", "vaneck", "first trust", "schwab etf",
}


# "This stock is listed on the London Stock Exchange" contains investment
# vocabulary ("stock") right next to an exchange name, so the vendor rule's
# framing test passes and LSEG is emitted as a holding. Venue constructions are
# therefore detected structurally and always win over the framing test.
VENUE_PATTERN = re.compile(
    r"(listed|trades?|trading|traded|quoted|delisted|ipo'?d|available)\s+"
    r"(on|at|via)\s+(the\s+)?$", re.I,
)


def looks_like_venue(text, start):
    return bool(VENUE_PATTERN.search(text[max(0, start - 40):start]))


def has_investment_framing(text, start, end):
    """Investment language tight around the span, not merely somewhere in the doc."""
    window = text[max(0, start - VENDOR_FRAMING_RADIUS): end + VENDOR_FRAMING_RADIUS]
    return bool(INVESTMENT_FRAMING.search(window))


# A run of comma/slash-separated uppercase tokens where several resolve to real
# tickers is one of the most common shapes in this sub ("XOM, SPGI, BTI, O, KO,
# HD, MO, PM, PFE, JNJ, MMM, AAPL"). Individually most of those carry no
# evidence at all - O and PM are blocked as jargon, KO/HD/MO/MMM are ordinary
# English - so a list like that yielded 6 of 12 names. Membership in a
# corroborated list is itself strong evidence, and it rescues exactly the short,
# word-like tickers the stoplist is otherwise forced to reject.
# Separator allows a comma/slash, run-on spaces, OR a single newline: real
# posts list holdings one per line as often as inline, and a space-only
# separator missed a 15-name portfolio list entirely. At most one newline, so a
# run cannot silently span two paragraphs.
_SEP = r"(?:[ \t]*[,/][ \t\n]*|[ \t]*\n[ \t]*|[ \t]+)"
TICKER_RUN = re.compile(r"\b[A-Z]{1,5}\b(?:" + _SEP + r"\b[A-Z]{1,5}\b){2,}")


def _is_shouted_prose(toks):
    """True when a run is capitalised English rather than a list of symbols.

    Pump posts shout: "GO BUY AS MUCH SHARES AS U CAN" contains the sub-run
    "AS U CAN", all three of which are real tickers, so both the ticker-ratio
    and any all-caps test pass. Surrounding case cannot discriminate either,
    because a genuine ticker list is *also* entirely uppercase - testing that
    rejected "ABBV BABA AMAT ..." outright.

    What separates them is vocabulary: a shouted sentence is made of ordinary
    English words, a holdings list mostly is not. Some real lists do contain
    word-like tickers (O, KO, MO, HD in a dividend list), so the bar is a
    clear majority rather than any occurrence.
    """
    if not toks:
        return True
    ordinary = sum(1 for t in toks if tier(t) in ("COMMON", "JARGON"))
    return ordinary / len(toks) > 0.7


def ticker_list_spans(text, by_ticker, min_known=3):
    """Character spans of comma-separated runs that are mostly real tickers."""
    spans = []
    for m in TICKER_RUN.finditer(text):
        toks = re.findall(r"\b[A-Z]{1,5}\b", m.group(0))
        known = sum(1 for t in toks if t in by_ticker)
        if known >= min_known and known >= len(toks) * 0.6:
            if _is_shouted_prose(toks):
                continue
            spans.append((m.start(), m.end()))
    return spans


def looks_like_citation(text, start, end):
    """True when the mention reads as citing a source rather than discussing a holding."""
    before = text[max(0, start - 40):start]
    after = text[end:end + 40]
    return bool(CITATION_PATTERN.search(before) or CITATION_TRAILING.match(after))


class Extractor:
    def __init__(self):
        self.by_ticker, self.name_aliases = build()
        self.name_aliases = dict(self.name_aliases)
        self.name_aliases.update(MANUAL_ALIASES)
        # Company names are matched by n-gram lookup, NOT by one giant regex
        # alternation. A 9k-branch alternation makes Python's re scan every
        # branch at every position: over a 57M-character corpus that ran at
        # roughly 20 documents/second and would not have finished. Token lookup
        # is O(tokens x max_alias_words) and independent of alias-set size.
        # The >=5 length floor keeps generic short tokens out, but it must not
        # apply to the hand-curated aliases: "nike", "coke" and "meta" are 4
        # characters and were being silently discarded, so Nike was unmatchable.
        self.aliases = {n: c for n, c in self.name_aliases.items()
                        if (n in MANUAL_ALIASES
                            or (len(n) >= 5
                                and n.replace(" ", "").replace("&", "").isalnum()))}
        self.max_alias_words = max((a.count(" ") + 1 for a in self.aliases), default=1)
        self.max_alias_words = min(self.max_alias_words, 4)
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
        toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(text)]
        i = 0
        while i < len(toks):
            hit = None
            # Longest n-gram first so "berkshire hathaway" beats "berkshire".
            for k in range(min(self.max_alias_words, len(toks) - i), 0, -1):
                phrase = " ".join(t[0].lower() for t in toks[i:i + k])
                cik = self.aliases.get(phrase)
                if cik:
                    hit = (k, cik, toks[i][1], toks[i + k - 1][2])
                    break
            if not hit:
                i += 1
                continue
            k, cik, s, e = hit
            i += k

            surface = text[s:e]
            alias = surface.lower()
            if alias in ETF_BRAND_ALIASES:
                continue
            evidence = ["company_name"]
            conf = 0.90
            tkr = self.cik_to_ticker.get(cik, "")
            if tkr in VENDOR_ROLE_TICKERS and (
                    looks_like_venue(text, s) or not has_investment_framing(text, s, e)):
                evidence.append("vendor_citation")
                conf = 0.50
            elif looks_like_citation(text, s, e):
                # Demoted below the 0.75 analysis floor rather than dropped, so
                # the hand-labelling gate can still measure this decision.
                evidence.append("citation_context")
                conf = 0.55
            elif self._alias_needs_proof(alias):
                if not surface[:1].isupper():
                    continue                       # "growth" is not Growth Corp
                if not VALUATION_CUE.search(_context(text, s, e)):
                    continue
                evidence.append("capitalised+valuation")
                conf = 0.75
            yield dict(ticker=self.cik_to_ticker.get(cik, ""), entity_id=cik,
                       channel="name", confidence=conf,
                       span=(s, e), evidence=evidence)

    def _bare(self, text, doc_cashtags, doc_names, runs=()):
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
            if (base not in PROSE_MARKERS
                    and SYMBOL_SYNTAX.search(text[max(0, m.start() - 2): m.end() + 3])):
                evidence.append("symbol_syntax")
            if any(a <= m.start() and m.end() <= b for a, b in runs):
                evidence.append("ticker_list")
            if VALUATION_CUE.search(ctx):
                evidence.append("valuation_language")
            if MONEY_CUE.search(ctx):
                evidence.append("numeric_context")

            # Membership in a holdings list is itself investment framing: a
            # vendor ticker sitting in "XOM, SPGI, BTI, O, KO, ..." is being
            # held, not cited.
            if (sym in VENDOR_ROLE_TICKERS
                    and "ticker_list" not in evidence
                    and not has_investment_framing(text, *m.span())):
                yield dict(ticker=sym, entity_id=meta["cik"], channel="bare",
                           confidence=0.50, span=m.span(),
                           evidence=evidence + ["vendor_citation"])
                continue

            if looks_like_citation(text, *m.span()):
                yield dict(ticker=sym, entity_id=meta["cik"], channel="bare",
                           confidence=0.55, span=m.span(),
                           evidence=evidence + ["citation_context"])
                continue

            strong = {"name_in_doc", "cashtag_in_doc", "symbol_syntax", "ticker_list"}
            has_strong = bool(strong & set(evidence))

            if t == "JARGON":
                if not has_strong:
                    continue
                # A single letter inside a list is far more likely to be a word
                # ("AS U CAN") than a ticker, so list membership alone does not
                # rescue it - it needs a cashtag or explicit symbol syntax.
                if base in SINGLE_LETTERS and evidence == ["ticker_list"]:
                    continue
                conf = 0.80 if "ticker_list" not in evidence else 0.88
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
        runs = ticker_list_spans(text, self.by_ticker)

        hits = list(self._cashtags(text)) + list(self._names(text))
        hits += list(self._bare(text, doc_cashtags, doc_names, runs))

        # Collapse overlapping hits on the same entity - "ON Semiconductor"
        # fires the name channel and the bare channel over nested spans, which
        # is one mention, not two. Keep the most confident, and merge evidence
        # so the surviving row records everything that corroborated it.
        # entity_id is an int CIK for SEC-known names and a "TIINGO:<ticker>"
        # string for delisted ones, so sort on its string form.
        hits.sort(key=lambda h: (str(h["entity_id"]), h["span"][0], -h["confidence"]))
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
