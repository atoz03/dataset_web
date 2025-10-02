import json
from pathlib import Path
from urllib.parse import quote_plus

import scrapy

from scraper.items import ScraperItem

class BingImagesSpider(scrapy.Spider):
    """
    A spider to crawl Bing Images for a list of keywords.

    This spider reads keywords from a file named 'keywords.txt' in the project's
    root directory. For each keyword, it performs a search on Bing Images and
    scrapes the URLs of the result images.
    """
    name = 'bing_images'
    allowed_domains = ['www.bing.com', 'bing.com']

    # Base URL for Bing Images search with pagination support.
    SEARCH_URL = 'https://www.bing.com/images/search?q={query}&first={first}&count={count}'

    custom_settings = {
        'DOWNLOAD_TIMEOUT': 30,
    }

    def __init__(self, keywords_file='keywords.txt', max_pages=1, page_size=35, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_root = Path(__file__).resolve().parents[2]
        self.keywords_file = keywords_file
        try:
            self.max_pages = max(1, int(max_pages))
        except (TypeError, ValueError):
            self.logger.warning("Invalid max_pages value '%s'; falling back to 1", max_pages)
            self.max_pages = 1

        try:
            self.page_size = max(10, min(100, int(page_size)))
        except (TypeError, ValueError):
            self.logger.warning("Invalid page_size value '%s'; falling back to 35", page_size)
            self.page_size = 35

    def start_requests(self):
        """
        Reads keywords from 'keywords.txt' and yields a request for each.
        """
        keywords_path = Path(self.keywords_file)
        if not keywords_path.is_absolute():
            keywords_path = self.project_root / keywords_path

        try:
            with keywords_path.open('r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.logger.error("Keywords file '%s' not found.", keywords_path)
            return

        if not keywords:
            self.logger.warning("No keywords found in '%s'.", keywords_path)
            return

        for keyword in keywords:
            self.logger.info("Starting crawl for keyword: %s", keyword)
            encoded_query = quote_plus(keyword)
            for page in range(self.max_pages):
                first = page * self.page_size
                url = self.SEARCH_URL.format(query=encoded_query, first=first, count=self.page_size)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={'query': keyword, 'page': page + 1},
                    dont_filter=True,
                )

    def parse(self, response):
        """
        Parses the Bing Images search result page to extract image URLs.
        Bing often embeds image data in a script tag as a JSON string.
        We look for a specific variable, 'm', which holds the data.
        """
        query = response.meta['query']
        page_number = response.meta.get('page')
        self.logger.info("Parsing results for query '%s' (page %s)", query, page_number)

        image_urls = []
        page_urls = []
        captions = []
        thumbnails = []
        metadata = []

        tiles = response.xpath('//a[contains(@class, "iusc")]')
        if not tiles:
            self.logger.error("No image tiles found for query '%s'. Bing markup may have changed.", query)
            return

        for tile in tiles:
            raw_meta = tile.attrib.get('m')
            if not raw_meta:
                continue

            try:
                meta_obj = json.loads(raw_meta)
            except json.JSONDecodeError:
                self.logger.debug("Failed to decode metadata for query '%s': %s", query, raw_meta[:120])
                continue

            image_url = meta_obj.get('murl')
            if not image_url:
                continue

            page_url = meta_obj.get('purl') or meta_obj.get('surl')
            caption = meta_obj.get('desc') or meta_obj.get('t')
            thumb = meta_obj.get('turl')

            image_urls.append(image_url)
            page_urls.append(page_url)
            captions.append(caption)
            thumbnails.append(thumb)
            metadata.append({
                'width': meta_obj.get('w'),
                'height': meta_obj.get('h'),
                'file_size': meta_obj.get('size'),
                'page_url': page_url,
                'thumbnail': thumb,
            })

        if not image_urls:
            self.logger.warning("No image URLs parsed for query '%s'.", query)
            return

        self.logger.info("Found %s images for query '%s' (page %s)", len(image_urls), query, page_number)

        yield ScraperItem(
            query=query,
            image_urls=image_urls,
            page_urls=page_urls,
            image_captions=captions,
            thumbnail_urls=thumbnails,
            source_site='bing.com',
            metadata={'tiles': metadata, 'page': page_number},
        )
