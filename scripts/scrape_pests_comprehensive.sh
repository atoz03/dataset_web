#!/bin/bash
# Comprehensive Pest Species Image Scraping Script
# Uses Pixabay API to scrape images for existing and new pest categories

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Comprehensive Pest Species Scraper${NC}"
echo -e "${GREEN}========================================${NC}"

# Check for API key
if [ -z "$PIXABAY_API_KEY" ]; then
    echo -e "${RED}ERROR: PIXABAY_API_KEY environment variable not set${NC}"
    echo -e "${YELLOW}Please register at: https://pixabay.com/api/docs/${NC}"
    echo -e "${YELLOW}Then export PIXABAY_API_KEY='your-key-here'${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pixabay API key found${NC}"

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo -e "${YELLOW}Project root: ${PROJECT_ROOT}${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}ERROR: Virtual environment not found at .venv${NC}"
    echo -e "${YELLOW}Please create it first: python3 -m venv .venv${NC}"
    exit 1
fi

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
SCRAPY="${PROJECT_ROOT}/.venv/bin/scrapy"

# Verify scrapy is installed
if [ ! -f "$SCRAPY" ]; then
    echo -e "${YELLOW}Installing scrapy...${NC}"
    "$PYTHON" -m pip install scrapy pillow --quiet
fi

# Create keywords file if needed
KEYWORDS_FILE="${PROJECT_ROOT}/web_scraper/keywords_pest_species.txt"

if [ ! -f "$KEYWORDS_FILE" ]; then
    echo -e "${RED}ERROR: Keywords file not found at ${KEYWORDS_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Keywords file found${NC}"

# Count keywords
KEYWORD_COUNT=$(grep -v '^#' "$KEYWORDS_FILE" | grep -v '^$' | wc -l | tr -d ' ')
echo -e "${YELLOW}Total keywords to scrape: ${KEYWORD_COUNT}${NC}"

# Navigate to web_scraper directory
cd "${PROJECT_ROOT}/web_scraper"

# Run Pixabay spider
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting Pixabay API scraping...${NC}"
echo -e "${GREEN}========================================${NC}"

"$SCRAPY" crawl pixabay_api \
    -a keywords_file=keywords_pest_species.txt \
    -a max_results=150 \
    -a per_page=150

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Scraping completed!${NC}"
echo -e "${GREEN}========================================${NC}"

# Count downloaded images
SCRAPED_DIR="${PROJECT_ROOT}/web_scraper/scraped_images"
if [ -d "$SCRAPED_DIR" ]; then
    IMAGE_COUNT=$(find "$SCRAPED_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
    echo -e "${GREEN}Total images scraped: ${IMAGE_COUNT}${NC}"
else
    echo -e "${YELLOW}No scraped_images directory found yet${NC}"
fi

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Review images in: ${SCRAPED_DIR}"
echo -e "2. Run deduplication: .venv/bin/python scripts/deduplicate_images.py --roots web_scraper/scraped_images"
echo -e "3. Manual review: Open docs/pest_manual_review.html"
echo -e "4. Import approved images: .venv/bin/python scripts/import_reviewed_pests.py"
echo -e "5. Rebuild JSONL: .venv/bin/python scripts/build_jsonl.py"
