#!/bin/bash
# Comprehensive scraping script for agricultural images
# Priority: Agriculture sites (GBIF) > Unsplash API

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Agricultural Image Scraping Pipeline${NC}"
echo -e "${GREEN}========================================${NC}"

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${RED}ERROR: Virtual environment not found${NC}"
    exit 1
fi

SCRAPY="${PROJECT_ROOT}/.venv/bin/scrapy"
cd "${PROJECT_ROOT}/web_scraper"

echo -e "${BLUE}Step 1: Scraping pest species from GBIF/iNaturalist${NC}"
echo -e "${YELLOW}Using keywords_pest_species.txt...${NC}"
"$SCRAPY" crawl agri_sites \
    -a keywords_file=keywords_pest_species.txt \
    -a max_api_results=150 \
    2>&1 | tee ../logs/scrape_pests_$(date +%Y%m%d_%H%M%S).log

echo ""
echo -e "${BLUE}Step 2: Scraping new pest species (scientific names)${NC}"
echo -e "${YELLOW}Using keywords_new_pests.txt...${NC}"
"$SCRAPY" crawl agri_sites \
    -a keywords_file=keywords_new_pests.txt \
    -a max_api_results=100 \
    2>&1 | tee ../logs/scrape_new_pests_$(date +%Y%m%d_%H%M%S).log

echo ""
echo -e "${BLUE}Step 3: Filling gaps with Unsplash API${NC}"
if [ -z "$UNSPLASH_API_KEY" ]; then
    echo -e "${RED}WARNING: UNSPLASH_API_KEY not set, skipping Unsplash scraping${NC}"
else
    echo -e "${YELLOW}Using keywords_missing_priority.txt...${NC}"
    "$SCRAPY" crawl unsplash_api \
        -a keywords_file=keywords_missing_priority.txt \
        -a max_pages=5 \
        -a per_page=30 \
        2>&1 | tee ../logs/scrape_unsplash_$(date +%Y%m%d_%H%M%S).log
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Scraping completed!${NC}"
echo -e "${GREEN}========================================${NC}"

# Generate statistics
echo -e "${BLUE}Generating statistics...${NC}"
SCRAPED_DIR="${PROJECT_ROOT}/web_scraper/scraped_images"
if [ -d "$SCRAPED_DIR" ]; then
    TOTAL_IMAGES=$(find "$SCRAPED_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
    RECENT_IMAGES=$(find "$SCRAPED_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) -mmin -60 | wc -l | tr -d ' ')
    
    echo -e "${GREEN}Total images in scraped_images/: ${TOTAL_IMAGES}${NC}"
    echo -e "${GREEN}Images scraped in last hour: ${RECENT_IMAGES}${NC}"
    
    echo ""
    echo -e "${BLUE}Top 20 categories by image count:${NC}"
    for dir in "$SCRAPED_DIR"/*; do
        if [ -d "$dir" ]; then
            name=$(basename "$dir")
            count=$(find "$dir" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
            echo "$name: $count"
        fi
    done | sort -t: -k2 -rn | head -20
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review scraped images"
echo "2. Run deduplication: .venv/bin/python scripts/deduplicate_images.py --roots web_scraper/scraped_images"
echo "3. Generate review manifest: .venv/bin/python scripts/generate_pest_review_manifest.py"
echo "4. Manual review: Open docs/pest_manual_review.html"
echo "5. Import approved: .venv/bin/python scripts/import_reviewed_pests.py"
echo "6. Rebuild JSONL: .venv/bin/python scripts/build_jsonl.py"
