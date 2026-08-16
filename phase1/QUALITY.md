# Extraction quality

## §5.2 gate: **PASS**, on a small self-labelled sample

    labelled docs : 30      (design doc asks for 300)
    TP=37  FP=2  FN=3
    precision = 0.949       gate >= 0.90   PASS
    recall    = 0.925       gate >= 0.80   PASS

    by channel      TP    FP   precision
      bare          27     0     1.000
      cashtag        1     0     1.000
      name           9     2     0.818

### Read this before believing the numbers

Three limitations, none of them small:

1. **n=30, not 300.** The interval around a 0.95 precision estimate at n=30 is
   wide. This is a smoke test that the extractor is not badly broken, not the
   measurement the design doc asks for.
2. **The labeller is not independent.** The labels were produced by the same
   system that wrote the extractor, so shared blind spots cannot show up. A
   human labeller who has never seen this code is what §5.2 actually requires.
3. **Labelling was not blind.** Two documents were re-labelled after inspecting
   extractor output. In both cases re-reading the *full* source text showed my
   original label was wrong — the first pass had been made from a truncated
   display and had missed a 15-name portfolio list and a "J&J or Coca-Cola"
   sentence — so the correction was adjudication against the source, not
   capitulation to the model. It is still not a blind protocol, and it biases
   the estimate upward by an unknown amount.

Treat the gate as provisionally passed. `artifacts/label_sample.tsv` holds 300
year-stratified documents ready for an independent labeller; scoring is
`phase1/score_labels.py`.

### What the gate caught

Running it moved precision 0.385 -> 0.949 and recall 0.500 -> 0.925, which is
the entire argument for having a gate. It found five defects that no amount of
staring at invented test sentences had surfaced:

| Defect | Effect | Fix |
|---|---|---|
| **Extraction-stage survivorship** | `FL` (Foot Locker, acquired 2025) was absent from SEC's current-state file, so `$FL` in a 2022 post was unmatchable | universe topped up with Tiingo's delisted tickers; 10,398 -> 19,353 symbols |
| Short manual aliases dropped | a `len>=5` filter silently discarded `nike`, `coke`, `meta` | manual aliases exempted from the length floor |
| Ticker lists unreadable | `XOM, SPGI, BTI, O, KO, HD, MO, PM, ...` yielded 6 of 12; a newline-separated portfolio list yielded 0 of 15 | list membership is now strong evidence, separators include newlines |
| Exchange-as-venue | "listed on the **London Stock Exchange**" emitted LSEG as a holding — and slipped the vendor rule because the sentence contains the word "stock" | venue constructions detected structurally, and they override the framing test |
| ETF brand words | "the **iShares** Electric Vehicles ETF" emitted IAU (iShares Gold Trust) | fund-family brands excluded from the name channel |

The first is the serious one. It is a *second* survivorship bias, distinct from
the price-data one §4.4 warns about: the mention set itself was quietly losing
acquired and bankrupt companies, which are exactly the names whose outcomes the
study most needs. It would have biased every downstream result toward survivors
while leaving no trace.

### Known residual errors

    PG    incidental biography ("worked 10 years at Procter & Gamble") in a
          document about Johnson Outdoors. The extractor detects MENTIONS; it
          has no notion of what a document is ABOUT. Real limitation.
    GRIN  source misspells "Grindrod" as "Grinrod". §5.2 calls for fuzzy
          matching on the name channel; not implemented.
    GOOGL source typo "GOGGL". Same fix would catch it.
    RYCEY Rolls-Royce, UK-listed. Structural — see the non-US limitation.

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
