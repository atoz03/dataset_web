import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import scrapy

from scraper.items import ScraperItem

class BingApiSpider(scrapy.Spider):
    """
    A spider to crawl Bing Image Search API for a list of keywords.
    
    This spider uses the Bing Image Search API (v7) to fetch image results.
    It requires an API key, which can be provided via the 'BING_SEARCH_API_KEY'
    environment variable or as a spider argument 'api_key'.
    """
    name = 'bing_api'
    allowed_domains = ['api.bing.microsoft.com']

    # Bing Image Search API v7 endpoint
    API_URL = 'https://api.bing.microsoft.com/v7.0/images/search?q={query}&count={count}&offset={offset}'

    custom_settings = {
        'DOWNLOAD_TIMEOUT': 30,
        'ROBOTSTXT_OBEY': False, # API usage does not require robots.txt checks
    }

    def __init__(self, keywords_file='keywords.txt', max_results=150, page_size=150, api_key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_root = Path(__file__).resolve().parents[2]
        self.keywords_file = keywords_file
        
        # Handle API Key
        self.api_key = api_key or os.environ.get('BING_SEARCH_API_KEY')
        if not self.api_key:
            self.logger.error("Bing API key not found. Please provide it via the 'BING_SEARCH_API_KEY' env var or 'api_key' argument.")

        try:
            # API max page size is 150
            self.page_size = min(150, int(page_size))
            self.max_results = int(max_results)
        except (TypeError, ValueError):
            self.logger.warning("Invalid numeric arguments; using defaults.")
            self.page_size = 150
            self.max_results = 150

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

        headers = {'Ocp-Apim-Subscription-Key': self.api_key}
        
        for keyword in keywords:
            self.logger.info("Starting API crawl for keyword: %s", keyword)
            encoded_query = quote_plus(keyword)
            
            # Paginate through results
            for offset in range(0, self.max_results, self.page_size):
                url = self.API_URL.format(query=encoded_query, count=self.page_size, offset=offset)
                yield scrapy.Request(
                    url=url,
                    headers=headers,
                    callback=self.parse,
                    meta={'query': keyword},
                    dont_filter=True,
                )

    def parse(self, response):
        """
        Parses the JSON response from the Bing Image Search API.
        """
        query = response.meta['query']
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response for query '%s'", query)
            return

        results = data.get('value', [])
        if not results:
            self.logger.warning("No results found for query '%s' in API response.", query)
            return

        image_urls = [item['contentUrl'] for item in results if 'contentUrl' in item]
        page_urls = [item['hostPageUrl'] for item in results if 'hostPageUrl' in item]
        captions = [item.get('name', '') for item in results]
        thumbnails = [item.get('thumbnailUrl', '') for item in results]
        
        metadata = [{
            'width': item.get('width'),
            'height': item.get('height'),
            'encodingFormat': item.get('encodingFormat'),
            'hostPageDisplayUrl': item.get('hostPageDisplayUrl'),
        } for item in results]

        self.logger.info("Found %d images for query '%s' via API", len(image_urls), query)

        yield ScraperItem(
            query=query,
            image_urls=image_urls,
            page_urls=page_urls,
            image_captions=captions,
            thumbnail_urls=thumbnails,
            source_site='bing.com_api',
            metadata={'results': metadata},
        )