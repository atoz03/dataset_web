import scrapy

class ScraperItem(scrapy.Item):
    """
    Defines the data structure for a scraped item.
    """
    # The search query that led to this item.
    # This will be used as the directory name for the downloaded images.
    query = scrapy.Field()

    # A list of image URLs found for the query.
    image_urls = scrapy.Field()

    # The source website (e.g., 'bing.com', 'google.com').
    source_site = scrapy.Field()

    # The list of pages that hosted the images (if available, aligned with image_urls).
    page_urls = scrapy.Field()

    # Any textual description, alt-text, or caption associated with the image.
    image_captions = scrapy.Field()

    # Optional thumbnails or preview assets.
    thumbnail_urls = scrapy.Field()

    # Holder for any extra metadata collected by a spider.
    metadata = scrapy.Field()

    # Field for the results of downloaded images (used by ImagesPipeline).
    images = scrapy.Field()
