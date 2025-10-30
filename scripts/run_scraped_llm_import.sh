#!/bin/bash
#
# Orchestrate: global dedupe -> LLM verify (8899 API, 32 workers) -> import -> rename(tag=web) -> dedupe per class
#
set -euo pipefail
export PYTHONUNBUFFERED=1

cd "/Volumes/disk/ECCV/dataset_web"

# Load base env if present
if [ -f .env.llm ]; then
  set -a
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env.llm | xargs)
  set +a
fi

# Force single-API mode: 8899 endpoint
export VLM_USE_MULTI_API=false
# Expect VLM_API_BASE from .env.llm; do not override if already set
export VLM_API_BASE=${VLM_API_BASE:-"https://88996.cloud"}
export VLM_WORKERS=32

LOG_DIR="logs/scraped_llm_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Scraped Images: LLM Verify + Import"
echo "=========================================="
echo "API:        $VLM_API_BASE"
echo "Workers:    $VLM_WORKERS"
echo "Log dir:    $LOG_DIR"
echo "=========================================="

step() {
  echo "\n---- $1 ----" | tee -a "$LOG_DIR/steps.log"
}

step "1/4 Global dedupe on scraped_images (1a exact, 1b near-class)"
# 1a) Global exact dedupe: fast bucket removal (ham=0, root scope)
.venv/bin/python3 -u scripts/deduplicate_images.py \
  --roots web_scraper/scraped_images \
  --blur-method both --blur-threshold 60 --tenengrad-threshold 700 \
  --ham-threshold 0 --near-scope root --action move \
  2>&1 | tee "$LOG_DIR/01a_dedupe_exact.log"

# 1b) Per-class near dedupe: reduce remaining near-duplicates with small Hamming distance
.venv/bin/python3 -u scripts/deduplicate_images.py \
  --roots web_scraper/scraped_images \
  --blur-method both --blur-threshold 60 --tenengrad-threshold 700 \
  --ham-threshold 3 --near-scope class --action move \
  2>&1 | tee "$LOG_DIR/01b_dedupe_near_class.log"

step "2/4 LLM verify (8899 API)"
.venv/bin/python3 -u llm_tools/verify_and_describe.py \
  --root web_scraper/scraped_images \
  --workers "$VLM_WORKERS" \
  --insecure \
  --skip-existing-metadata \
  2>&1 | tee "$LOG_DIR/02_llm_verify.log"

step "3/4 Import accepted to datasets/* with __web__ tag"
.venv/bin/python3 -u scripts/import_llm_verified_scraped.py \
  --tag web \
  2>&1 | tee "$LOG_DIR/03_import.log"

step "4/4 Final dedupe on touched dataset roots"
.venv/bin/python3 -u scripts/deduplicate_images.py \
  --roots datasets/diseases datasets/crops datasets/pests \
  --blur-method both --blur-threshold 60 --tenengrad-threshold 700 \
  --ham-threshold 3 --near-scope class --action move \
  2>&1 | tee "$LOG_DIR/04_dedupe_datasets.log"

echo "\n✅ Done. See logs in $LOG_DIR"
