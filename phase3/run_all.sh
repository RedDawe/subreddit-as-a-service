#!/usr/bin/env bash
# Full Phase 3 run. Resumable: re-run after a quota pause and it continues.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && source .env
export PYTHONPATH=phase2:phase3

python3 phase3/select_cohort.py data/mentions_posts.ndjson data/cohort_plan.json \
    --min-authors 3 --n-controls 200
python3 phase3/fetch_prices.py data/cohort_plan.json data/prices
python3 phase3/outcomes.py    data/cohort_plan.json data/prices data/analysis_table.ndjson
python3 phase3/analyses.py       data/analysis_table.ndjson --out artifacts/results_core.json
python3 phase3/analyses_extra.py data/analysis_table.ndjson data/prices \
    --out artifacts/results_extra.json
