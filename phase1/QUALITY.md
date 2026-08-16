# Extraction quality — findings so far

Design doc §5.2 requires precision ≥ 0.90 and recall ≥ 0.80 against 300
hand-labelled documents, with both numbers reported. **That gate has not been
run yet** — it needs human labelling (`make_label_sample.py` → fill in the
`gold_tickers` column → `score_labels.py`). Nothing below substitutes for it.

What follows is developer QA on real extracted output: the false-positive
classes found by inspecting every distinct matched surface string, and what was
changed in response. It is recorded because §5.2 is explicit that an extraction
stage with unmeasured error rates invalidates everything downstream — so the
error modes should at least be *named* before the formal gate runs.

## False-positive classes found and fixed

| Class | Example | Damage | Fix |
|---|---|---|---|
| Currency codes | `RM 829,919` → Regional Management | 16 hits in one document | ISO currency codes added to the JARGON tier |
| Investor surnames | `Benjamin Graham` → Graham Holdings | 13 hits | `PERSON_NAMES` blocklist — in a value sub these are people, not tickers |
| Generic head words | `Capital One` → alias `capital`; `United Rentals` → `united` | matched ordinary prose | head-word aliases now require corpus-rarity, not just length ≥ 6 |
| Generic single-word names | `Market`, `Safety`, `Security` | matched ordinary prose | same rarity test applied to all single-word aliases |

Aliases dropped from 10,327 to 9,156. The rarity test is `wordfreq.zipf_frequency
< 3.0` (rarer than ~1 per million words) rather than a hand-written list, so it
stays reproducible and does not need maintaining.

Length is *not* a usable filter here, which was the initial mistake: `capital`,
`united`, `graham`, `security` and `safety` are all ≥ 6 characters.

## The residual false-positive class: uncorroborated acronyms

The surviving error mode is domain acronyms that happen to be tickers, in
documents with no corroborating evidence:

    TDF  <- "TDF (tenofovir disoproxil fumarate)-based" in a Gilead writeup
            resolves to Templeton Dragon Fund. 4 hits, confidence 0.70, evidence []

These land in the `CLEAR` tier (not English, not jargon) with no supporting
signal, and are exactly what the lowest confidence band is for.

## Recommended operating point: `--min-conf 0.75`

| threshold | mentions | entities | TDF false positives |
|---|---|---|---|
| 0.70 | 297 | 96 | 4 |
| 0.75 | 268 | 80 | 0 |
| 0.85 | 266 | 79 | 0 |

0.75 removes the known FP class while retaining ~90% of mentions. The 0.70 band
is uncorroborated-but-plausible and is kept in the output rather than discarded,
so the hand-labelling exercise can measure it instead of having the decision
pre-made by this file.

## Correct extractions worth recording

Spot-checking confirmed the pipeline handles the cases §5.2 says are hard:

    GBX  <- "GBX - A GREAT VALUE PICK?" ... "Greenbrier's profits"   conf 0.93
    DX   <- "3rd place would be DX" ... "DX looks like a good value" conf 0.93
    ALL  <- "ALL is a great insurer, Allstate has a moat"            conf 0.88
    KEY  <- "KEY: my thesis is that the market cap is too low"       conf 0.88
    ON   <- "ON Semiconductor is cheap. ON trades at 12x earnings"   conf 0.88

and rejects the §5.2 hazard sentences outright:

    "I did some DD on the CEO and the EPS growth. ROIC is 14%."   -> nothing
    "all of it is key to be honest, so we play it safe"           -> nothing
    "My honest opinion is that growth stocks are expensive"       -> nothing

## Performance note

The company-name channel originally used a single regex alternation over ~9,000
aliases. Python's `re` scans every branch at every position, so over the 57M-character
corpus it ran at roughly 20 documents/second and would not have completed. It now
tokenises and looks up 1- to 4-grams in a dict, which is O(tokens) and independent
of alias-set size: **62,519 documents in 91 seconds**, with identical output on the
regression cases above.

## Known limitation carried forward

`universe.py` builds from SEC EDGAR's **current-state** ticker file. It gives no
point-in-time membership, so a ticker reassigned between the mention date and
today resolves to today's owner — the exact hazard §4.4 names (FB→META, recycled
dead tickers). This must be fixed with EDGAR former-names data before any return
is computed. It does not affect A1, which counts distinct entities rather than
pricing them.
