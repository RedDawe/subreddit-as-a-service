#!/usr/bin/env bash
# Full pipeline. Every stage is resumable: re-run after a quota pause and it
# continues from where it stopped.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && source .env
export PYTHONPATH=phase1:phase2:phase3

# --- Phase 0: corpus -------------------------------------------------------
python3 phase0/arctic_shift_fetch.py posts    2010-09-01 2026-08-16 data/posts
python3 phase0/arctic_shift_fetch.py comments 2019-01-01 2022-01-01 data/comments
python3 phase0/score_check.py data/posts/posts.ndjson

# --- Phase 1: extraction, gate, panel --------------------------------------
python3 phase1/extract.py data/posts/posts.ndjson    data/mentions_posts.ndjson    post
python3 phase1/extract.py data/comments/comments.ndjson data/mentions_comments.ndjson comment
python3 phase1/score_labels.py artifacts/label_sample.tsv data/mentions_posts.ndjson
python3 phase0/a1_base_rate.py data/mentions_posts.ndjson 0.75
python3 phase1/build_panel.py data/mentions_posts.ndjson artifacts/mention_panel.csv \
    --posts data/posts/posts.ndjson --min-conf 0.75

# --- Phase 3: prices and analyses ------------------------------------------
python3 phase3/test_outcomes.py
python3 phase3/test_analyses.py
python3 phase3/select_cohort.py data/mentions_posts.ndjson data/cohort_plan.json \
    --min-authors 4 --n-controls 220
python3 phase3/fetch_prices.py data/cohort_plan.json data/prices
python3 phase3/outcomes.py data/cohort_plan.json data/prices data/analysis_table.ndjson
python3 phase3/analyses.py       data/analysis_table.ndjson --out artifacts/results_core.json
python3 phase3/analyses_extra.py data/analysis_table.ndjson data/prices \
    --out artifacts/results_extra.json
python3 phase3/writeup.py artifacts/results_core.json artifacts/results_extra.json \
    artifacts/WRITEUP.md --horizon 5
