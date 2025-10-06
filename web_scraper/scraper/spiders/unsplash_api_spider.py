import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import scrapy

from scraper.items import ScraperItem

class UnsplashApiSpider(scrapy.Spider):
    """
    A spider to crawl the Unsplash API for a list of keywords.
    
    This spider uses the Unsplash API to fetch high-quality images.
    It requires an Access Key, which can be provided via the 'UNSPLASH_API_KEY'
    environment variable or as a spider argument 'api_key'.
    """
    name = 'unsplash_api'
    allowed_domains = ['api.unsplash.com', 'images.unsplash.com']

    # Unsplash API endpoint for searching photos
    API_URL = 'https://api.unsplash.com/search/photos?query={query}&page={page}&per_page={per_page}'

    custom_settings = {
        'DOWNLOAD_TIMEOUT': 30,
        'ROBOTSTXT_OBEY': False, # API usage does not require robots.txt checks
        'DOWNLOAD_DELAY': 2, # Add a 2-second delay to respect API rate limits
    }

    def __init__(self, keywords_file='keywords.txt', max_pages=5, per_page=30, api_key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_root = Path(__file__).resolve().parents[2]
        self.keywords_file = keywords_file
        
        # Handle API Key
        self.api_key = api_key or os.environ.get('UNSPLASH_API_KEY')
        if not self.api_key:
            self.logger.error("Unsplash API key not found. Please provide it via the 'UNSPLASH_API_KEY' env var or 'api_key' argument.")

        try:
            # API max per_page is 30
            self.per_page = min(30, int(per_page))
            self.max_pages = int(max_pages)
        except (TypeError, ValueError):
            self.logger.warning("Invalid numeric arguments; using defaults.")
            self.per_page = 30
            self.max_pages = 5

    def start_requests(self):
        """
        Reads keywords and yields API requests.
        """
        if not self.api_key:
            return # Stop if no API key

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

        headers = {'Authorization': f'Client-ID {self.api_key}'}
        
        for keyword in keywords:
            self.logger.info("Starting Unsplash API crawl for keyword: %s", keyword)
            encoded_query = quote_plus(keyword)
            
            for page in range(1, self.max_pages + 1): # Unsplash pages are 1-indexed
                url = self.API_URL.format(query=encoded_query, page=page, per_page=self.per_page)
                yield scrapy.Request(
                    url=url,
                    headers=headers,
                    callback=self.parse,
                    meta={'query': keyword, 'page': page},
                    dont_filter=True,
                )

    def parse(self, response):
        """
        Parses the JSON response from the Unsplash API.
        """
        query = response.meta['query']
        page = response.meta['page']
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response for query '%s', page %d", query, page)
            return

        results = data.get('results', [])
        if not results:
            self.logger.warning("No results found for query '%s' on page %d.", query, page)
            return

        image_urls = [item['urls']['regular'] for item in results if 'urls' in item and 'regular' in item['urls']]
        page_urls = [item['links']['html'] for item in results if 'links' in item and 'html' in item['links']]
        captions = [item.get('alt_description') or item.get('description', '') for item in results]
        thumbnails = [item['urls']['thumb'] for item in results if 'urls' in item and 'thumb' in item['urls']]
        
        metadata = [{
            'id': item.get('id'),
            'width': item.get('width'),
            'height': item.get('height'),
            'color': item.get('color'),
            'user': item.get('user', {}).get('name'),
        } for item in results]

        self.logger.info("Found %d images for query '%s' (page %s)", len(image_urls), query, page)

        yield ScraperItem(
            query=query,
            image_urls=image_urls,
            page_urls=page_urls,
            image_captions=captions,
            thumbnail_urls=thumbnails,
            source_site='unsplash.com_api',
            metadata={'results': metadata},
        )