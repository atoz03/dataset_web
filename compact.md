# Context Transfer (Rice Growth Collection) — Dec 2025

Project: `/Volumes/disk/ECCV/dataset_web`

Goal: Gather high-quality rice growth imagery (tillering → jointing → booting/panicle initiation → heading → grain filling) for 720p@24fps 2–5s clips & LoRA training. Target ≈100 images per stage, multi-weather/viewpoint, clear/no watermark. Proxy: socks5h://127.0.0.1:7895. Used Unsplash + GBIF (via `agri_sites`), no Bing.

Key files/changes:
- `web_scraper/keywords/keywords_rice_growth.txt`: full stage/timelapse keywords (EN + zh).
- `web_scraper/keywords/keywords_rice_growth_gap.txt`: shortage-only keywords (jointing/booting/panicle-initiation/heading/heading-panicles/grain-filling/milk + zh).
- `web_scraper/site_configs/agriculture_sites.json`: keyword_overrides map new stage keywords → `Oryza sativa` (GBIF).
- Crawls run (proxy + Unsplash key provided by user). GBIF run: `max_api_results=120`. Unsplash runs multiple times (max_pages up to 4, per_page 30).
- Cleaning: `scripts/03_cleaning/deduplicate_images.py` with `--min-width 224 --min-height 224 --blur-method both --blur-threshold 60 --tenengrad-threshold 700 --ham-threshold 3 --near-scope class --action move`.
- Renaming: `scripts/03_cleaning/bulk_rename_by_class.py --tag web`.
- Counts (after last cleaning, paths under `web_scraper/scraped_images`):
  - tillering: 139
  - jointing: 114
  - booting: 110
  - panicle initiation: 82
  - heading: 48
  - heading panicles: 58
  - grain filling: 59
  - milk stage: 25
  - timelapse/time-series: 27
- Trash/rejects: `.trash` 912 (includes blur/dupe/small), `.rejected_by_llm` 926 untouched.
- One stray folder: `web_scraper/scraped_images/High-need stages to top up counts` (1 img) from a commented keyword.

Next actions (suggested):
1) To hit 100 per stage, focus on heading, grain filling, milk, panicle initiation. Run Unsplash again with `keywords_rice_growth_gap.txt`, e.g. `max_pages=4`, `per_page=30`, proxy on. (Monitor rate limits.)
2) After crawl: rerun dedup + rename + count; remove the stray `High-need...` folder.
3) Optional: another GBIF pass (same keywords) if Unsplash insufficient; still mapped to `Oryza sativa`.

Notes:
- Do not store secrets in repo; set Unsplash key via env before running spiders.
- Images currently reside in `web_scraper/scraped_images/<class>/<source>/...` with filenames already normalized (`__web__`). 
