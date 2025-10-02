from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem
import scrapy
import hashlib


def _sanitize_component(value: str, fallback: str) -> str:
    """Return a filesystem-safe path component."""
    if not value:
        value = fallback
    safe = "".join(c for c in value if c.isalnum() or c in (" ", "_", "-"))
    safe = safe.strip()
    return safe or fallback

class CustomImagesPipeline(ImagesPipeline):
    """
    A custom image pipeline that saves images into subdirectories named after
    the search query.
    """

    def file_path(self, request, response=None, info=None, *, item=None):
        """
        Overrides the default file_path method to save images in a folder
        named after the item's query.
        e.g., images/Corn rust leaf/xxxxxxxx.jpg
        """
        adapter = ItemAdapter(item)
        query = adapter.get('query')
        source_site = adapter.get('source_site')

        safe_query = _sanitize_component(query, 'misc')
        safe_source = _sanitize_component(source_site, 'unknown')

        # Use a hash of the URL as the filename to avoid duplicates and long names
        image_guid = hashlib.sha1(request.url.encode()).hexdigest()
        return f"{safe_query}/{safe_source}/{image_guid}.jpg"

    def get_media_requests(self, item, info):
        """
        Yields a Request object for each image URL in the item.
        """
        adapter = ItemAdapter(item)
        image_urls = adapter.get('image_urls', [])
        for image_url in image_urls:
            yield scrapy.Request(image_url)

    def item_completed(self, results, item, info):
        """
        Handles the completion of item processing.
        'results' is a list of 2-tuples (success, image_info_or_failure).
        """
        image_paths = [x['path'] for ok, x in results if ok]
        adapter = ItemAdapter(item)
        if not image_paths:
            raise DropItem(f"Item contains no images: {adapter.get('query', '<unknown>')}")

        adapter['images'] = image_paths
        return item
