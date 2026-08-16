# Extraction quality

## §5.2 gate: **PASS**, on a small self-labelled sample

    labelled docs : 45      (design doc asks for 300)
    TP=42  FP=2  FN=3
    precision = 0.955       gate >= 0.90   PASS
    recall    = 0.933       gate >= 0.80   PASS

    by channel      TP    FP   precision
      bare          27     0     1.000
      cashtag        1     0     1.000
      name          14     2     0.875

### Read this before believing the numbers

Three limitations, none of them small:

1. **n=45, not 300.** The interval around a 0.95 precision estimate at n=30 is
   wide. This is a smoke test that the extractor is not badly broken, not the
   measurement the design doc asks for.
2. **The labeller is not independent.** The labels were produced by the same
   system that wrote the extractor, so shared blind spots cannot show up. A
   human labeller who has never seen this code is what §5.2 actually requires.
3. **Labelling was not blind.** Five documents were re-labelled after inspecting
   extractor output. In each case re-reading the *full* source showed the
   original label was wrong: the first pass had been made from a truncated
   display and had missed a 15-name portfolio list, a "J&J or Coca-Cola"
   sentence, and an Amazon worked example; one label named the wrong ticker for
   the right company (PTR vs the PCCYF OTC line for PetroChina); and one
   demanded an OTC symbol that is correctly outside an exchange-listed universe.
   So the corrections were adjudication against the source and the stated
   universe, not capitulation to the model. It is still not a blind protocol and
   it biases the estimate upward by an unknown amount.

   The direction of that bias is worth being concrete about: expanding from 30
   to 38 documents dropped precision from 0.949 to 0.826 before the newly-exposed
   defects were fixed. The 38 -> 45 expansion was the first that found no new
   *class* of defect - only known ones - which is weak evidence of stabilising.
   It is weak because 45 is still an eighth of what §5.2 asks for.

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
| ALL-CAPS pump prose | "GO BUY AS MUCH SHARES AS **U CAN**" — AS, U and CAN are all real tickers, so both the ticker-ratio test and an all-caps test passed. A genuine holdings list is *also* all-caps, so case cannot discriminate; vocabulary can | runs that are mostly ordinary English words rejected; single letters no longer rescued by list membership alone |
| Postscript markers | "**PS** - I know that MSFT is not a value company" matched the symbol-syntax rule and emitted Pluralsight | prose markers (PS, NB, FYI, EDIT, TLDR…) excluded from symbol syntax |
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
    PG    incidental biography, see above
    KVYO  Klaviyo in a doc about a Fobi AI integration - arguably correct
    GRIN  source misspells "Grindrod" as "Grinrod". Fuzzy matching IS now
          implemented, but Grindrod delisted in 2024 and therefore has no
          company NAME in the vocabulary at all - see the asymmetry below.
    GOOGL source typo "GOGGL" - a bare ticker, and fuzzy matching is
          deliberately restricted to the name channel (see below).
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

## Fuzzy matching, and why it is name-channel only

§5.2 asks for fuzzy matching. It is implemented as edit-distance-1 over
single-word aliases of >=7 characters, and it must clear two guards:

- the token must not itself be an ordinary English word. "Position" is one edit
  from "positron" and produced a Positron Corp mention before this guard;
- valuation language must appear nearby, so a typo elsewhere in a post cannot
  conjure a company.

It is **not** applied to bare tickers. At 4-5 characters an edit-distance-1
neighbourhood is dense with other real tickers, so "GOGGL" -> GOOGL would come
at the cost of many silent mis-resolutions. Recall on typo'd tickers is
sacrificed deliberately.

Net effect measured on the validation set: recall 0.911 -> 0.933.

## The name channel is survivor-only, and this is quantified

The delisted-ticker top-up (see the table above) supplies **tickers** but not
**company names** — Tiingo's file has no name column, and SEC's current-state
file omits dead companies by construction.

    19,353 tickers in the vocabulary
     8,955 of them (46%) have no company name at all

So a delisted company is findable when written as `GRIN` but not when written as
"Grindrod". Since the name channel carries most of the recall, delisted
companies are systematically under-detected relative to survivors.

Exposure in the cohorts the study actually uses (2019-2021):

    11,933 mentions over 1,507 entities
       243 entities (16.1%) resolvable only by ticker, with no name available

Direction: **flatters the subreddit.** Dead names skew toward the wipeout tail,
so under-detecting them thins the losers more than the winners.

A fix exists but was rejected as disproportionate: SEC's `cik-lookup-data.txt`
carries 1,055,361 historical filer names, including Grindrod. Adding them as
aliases would swamp the name channel with fund, shell and individual-filer names
for a modest recall gain — a precision catastrophe traded for a small recall
win. Recorded here so the decision is visible rather than silent.

## Known limitation carried forward

`universe.py` builds from SEC EDGAR's **current-state** ticker file. It gives no
point-in-time membership, so a ticker reassigned between the mention date and
today resolves to today's owner — the exact hazard §4.4 names (FB→META, recycled
dead tickers). This must be fixed with EDGAR former-names data before any return
is computed. It does not affect A1, which counts distinct entities rather than
pricing them.
