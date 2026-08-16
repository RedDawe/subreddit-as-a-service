"""Stoplist tiers for bare-ticker extraction (design doc 5.2).

The problem the doc names: uppercase tokens like A, ALL, IT, ON, KEY, OPEN, DD,
CEO, EPS, ROIC, SO, BE, PLAY, AI are *real tickers* as well as ordinary words or
finance jargon. Dropping them costs recall on genuine names (Allstate, KeyCorp,
ON Semiconductor); keeping them destroys precision.

So this is not one stoplist but three tiers, which the extractor turns into
different evidence requirements rather than a hard include/exclude:

  JARGON  - never a ticker in this sub unless cashtagged. "DD", "EPS", "ROIC".
  COMMON  - ordinary English; needs corroborating context. "ALL", "ON", "KEY".
  CLEAR   - everything else; accepted on a plain uppercase match.

Tier membership is derived from corpus frequency (wordfreq) rather than
hand-listed, so it stays defensible and reproducible; the hand-written set is
reserved for finance jargon, which general English frequency does not capture.
"""

from functools import lru_cache

# Finance/Reddit jargon and acronyms that collide with real tickers.
# These are cashtag-only: a bare occurrence is assumed NOT to be a ticker.
JARGON = {
    # analysis vocabulary
    "DD", "EPS", "ROIC", "ROE", "ROA", "PE", "PEG", "EV", "FCF", "DCF", "WACC",
    "CAGR", "TAM", "SAM", "COGS", "SGA", "EBIT", "EBITDA", "NAV", "BV", "PB",
    "PS", "YOY", "QOQ", "TTM", "LTM", "GAAP", "CAPEX", "OPEX", "ARR", "MRR",
    "KPI", "IPO", "SPAC", "ETF", "REIT", "LBO", "MOAT", "MOS",
    # roles / entities
    "CEO", "CFO", "COO", "CTO", "IR", "SEC", "FED", "IRS", "FTC", "DOJ", "GAAP",
    # market chatter
    "ATH", "ATL", "YOLO", "FOMO", "HODL", "TA", "FA", "PT", "SL", "TP",
    "OTC", "NYSE", "AH", "PM", "EOD", "EOY",
    # macro
    "GDP", "CPI", "PPI", "PMI", "QE", "QT", "USD", "EUR", "GBP", "JPY", "CNY",
    # internet shorthand
    "IMO", "IMHO", "TLDR", "TL", "DR", "AFAIK", "IIRC", "OP", "EDIT", "NSFW",
    "LOL", "IDK", "AKA", "FYI", "BTW", "ELI", "ETA", "PSA", "US", "USA", "UK",
    "EU", "AI", "ML", "EV",   # EV/AI are tickers but overwhelmingly not here
}

# Single letters are never accepted bare - too noisy - though many are valid
# tickers (A = Agilent, F = Ford, T = AT&T). Cashtag channel still catches them.
SINGLE_LETTERS = {chr(c) for c in range(ord("A"), ord("Z") + 1)}

COMMON_WORD_RANK = 20_000   # tokens inside the top-N English words need context


@lru_cache(maxsize=1)
def _english_ranks():
    """word -> frequency rank, for the top COMMON_WORD_RANK English words."""
    try:
        from wordfreq import top_n_list
        return {w: i for i, w in enumerate(top_n_list("en", COMMON_WORD_RANK))}
    except ImportError:                                  # pragma: no cover
        # Degraded but functional: the jargon tier still applies.
        return {}


def tier(token):
    """Classify an uppercase candidate token into an evidence tier."""
    if token in SINGLE_LETTERS:
        return "JARGON"
    if token in JARGON:
        return "JARGON"
    rank = _english_ranks().get(token.lower())
    if rank is not None and rank < COMMON_WORD_RANK:
        return "COMMON"
    return "CLEAR"


if __name__ == "__main__":
    for t in ("NVDA", "ALL", "ON", "KEY", "OPEN", "DD", "PLAY", "BRK", "MSFT",
              "IT", "SO", "BE", "A", "GOOG", "TSM", "CROX", "AI"):
        print(f"  {t:6} -> {tier(t)}")
