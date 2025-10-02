import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode, urljoin, urlparse

import scrapy
from scrapy.http import Response

from scraper.items import ScraperItem


class AgricultureSitesSpider(scrapy.Spider):
    """Multi-source spider that targets agriculture-focused sites/APIs."""

    name = "agri_sites"
    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "RETRY_ENABLED": True,
    }

    def __init__(
        self,
        keywords_file: str = "keywords.txt",
        config_file: str = "site_configs/agriculture_sites.json",
        max_articles_per_keyword: int = 40,
        max_api_results: int = 1000,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.project_root = Path(__file__).resolve().parents[2]
        self.keywords = self._load_keywords(keywords_file)
        self.sites = self._load_sites(config_file)
        self.max_articles_per_keyword = max(1, int(max_articles_per_keyword))
        self.max_api_results = max(1, int(max_api_results))
        self.site_keyword_scheduled = defaultdict(int)
        self.api_keyword_counts = defaultdict(int)

        # Populate allowed domains dynamically for HTML sites.
        allowed: List[str] = []
        for site in self.sites:
            if not site.get("enabled", True):
                continue
            if site["type"] == "html":
                allowed.extend(site.get("allowed_domains", []))
            if site.get("base_url"):
                allowed.append(urlparse(site["base_url"]).netloc)
            allowed.extend(site.get("media_domains", []))
        if allowed:
            self.allowed_domains = allowed

    def _load_keywords(self, keywords_file: str) -> List[str]:
        path = Path(keywords_file)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            self.logger.warning("Keywords file '%s' not found.", path)
            return []
        with path.open("r", encoding="utf-8") as fh:
            keywords = [
                line.strip()
                for line in fh
                if line.strip() and not line.lstrip().startswith("#")
            ]
        return keywords

    def _load_sites(self, config_file: str) -> List[Dict[str, Any]]:
        path = Path(config_file)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            raise FileNotFoundError(f"Config file '{path}' not found.")
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("Site configuration must be a list of site definitions.")
        return data

    def start_requests(self):
        if not self.keywords:
            self.logger.error("No keywords provided; aborting crawl.")
            return
        if not self.sites:
            self.logger.error("No site configurations available; aborting crawl.")
            return

        for site in self.sites:
            if not site.get("enabled", True):
                continue
            site_name = site.get("name", site.get("type", "unknown"))
            site["name"] = site_name
            if site["type"] == "html":
                search_conf = site.get("search", {})
                if not search_conf.get("url"):
                    self.logger.warning("Site '%s' missing search URL; skipping.", site_name)
                    continue
                for keyword in self.keywords:
                    formatted_url = search_conf["url"].format(query=quote_plus(keyword))
                    yield scrapy.Request(
                        url=formatted_url,
                        callback=self.parse_html_search,
                        meta={
                            "site": site,
                            "keyword": keyword,
                            "page": 1,
                        },
                        dont_filter=True,
                    )
            elif site["type"] == "api":
                yield from self._schedule_api_requests(site)
            elif site["type"] == "commons":
                yield from self._schedule_commons_requests(site)
            elif site["type"] == "gbif":
                yield from self._schedule_gbif_requests(site)
            else:
                self.logger.warning("Unsupported site type '%s'", site["type"])

    def parse_html_search(self, response: Response):
        site = response.meta["site"]
        keyword = response.meta["keyword"]
        page = response.meta.get("page", 1)
        site_name = site.get("name", "unknown")
        search_conf = site.get("search", {})
        listing_selector = search_conf.get("listing_selector")
        if not listing_selector:
            self.logger.error("Site '%s' missing listing_selector; skipping.", site_name)
            return

        results = response.css(listing_selector)
        if not results:
            self.logger.info("No search results for '%s' on site '%s' (page %s).", keyword, site_name, page)

        max_pages = max(1, int(search_conf.get("max_pages", 1)))
        for result in results:
            link = result.css(search_conf.get("link_selector", "")).get()
            if not link:
                continue
            absolute_link = urljoin(response.url, link)
            limit = min(site.get("max_articles_per_keyword", self.max_articles_per_keyword), self.max_articles_per_keyword)
            counter_key = f"{site_name}|{keyword}"
            if self.site_keyword_scheduled[counter_key] >= limit:
                continue
            self.site_keyword_scheduled[counter_key] += 1

            title = self._extract_clean_text(result, search_conf.get("title_selector"))
            snippet = self._extract_clean_text(result, search_conf.get("snippet_selector"))

            yield response.follow(
                absolute_link,
                callback=self.parse_html_detail,
                meta={
                    "site": site,
                    "keyword": keyword,
                    "listing_title": title,
                    "listing_snippet": snippet,
                    "origin_url": absolute_link,
                },
            )

        # Pagination
        next_selector = search_conf.get("next_page_selector")
        if page < max_pages and next_selector:
            next_href = response.css(next_selector).get()
            if next_href:
                next_url = urljoin(response.url, next_href)
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_html_search,
                    meta={
                        "site": site,
                        "keyword": keyword,
                        "page": page + 1,
                    },
                    dont_filter=True,
                )

    def parse_html_detail(self, response: Response):
        site = response.meta["site"]
        keyword = response.meta["keyword"]
        site_name = site.get("name", "unknown")
        detail_conf = site.get("detail", {})
        gallery_selector = detail_conf.get("gallery_selector")
        if not gallery_selector:
            self.logger.warning("Site '%s' missing gallery_selector; skipping item extraction.", site_name)
            return

        image_urls: List[str] = []
        thumbnails: List[str] = []
        captions: List[Optional[str]] = []

        allow_filters = detail_conf.get("filters", {}).get("allow_substrings", [])
        deny_filters = detail_conf.get("filters", {}).get("deny_substrings", [])

        for block in response.css(gallery_selector):
            original = self._extract_clean_attr(block, detail_conf.get("original_attr"))
            thumbnail = self._extract_clean_attr(block, detail_conf.get("thumbnail_attr"))
            caption = self._extract_first_available(block, detail_conf.get("caption_attrs", []))

            if original:
                original = urljoin(response.url, original)
            if thumbnail:
                thumbnail = urljoin(response.url, thumbnail)

            target_url = original or thumbnail
            if not target_url:
                continue
            if allow_filters and not any(substr in target_url for substr in allow_filters):
                continue
            if any(substr in target_url for substr in deny_filters):
                continue

            image_urls.append(target_url)
            thumbnails.append(thumbnail or target_url)
            captions.append(caption)

        if not image_urls:
            self.logger.debug("No images extracted for '%s' on '%s'.", keyword, response.url)
            return

        metadata = {
            "site_name": site_name,
            "source_url": response.url,
            "listing_title": response.meta.get("listing_title"),
            "listing_snippet": response.meta.get("listing_snippet"),
        }

        yield ScraperItem(
            query=keyword,
            image_urls=image_urls,
            thumbnail_urls=thumbnails,
            image_captions=captions,
            page_urls=[response.meta.get("origin_url", response.url)] * len(image_urls),
            source_site=site_name,
            metadata=metadata,
        )

    def _schedule_api_requests(self, site: Dict[str, Any]):
        site_name = site.get("name", "api")
        query_conf = site.get("query", {})
        base_url = site.get("base_url")
        if not base_url or not query_conf.get("param"):
            self.logger.warning("API site '%s' misconfigured; skipping.", site_name)
            return

        params = query_conf.get("params", {})
        max_pages = int(query_conf.get("max_pages", 1))
        per_page = int(query_conf.get("params", {}).get("per_page", 50))
        if per_page > 0:
            max_allowed = math.ceil(self.max_api_results / per_page)
            max_pages = min(max_pages, max_allowed)
        for keyword in self.keywords:
            for page in range(1, max_pages + 1):
                query_params = {**params}
                query_params[query_conf["param"]] = keyword
                query_params["page"] = page
                url = f"{base_url}?{urlencode(query_params)}"
                yield scrapy.Request(
                    url,
                    callback=self.parse_api,
                    meta={
                        "site": site,
                        "keyword": keyword,
                        "page": page,
                    },
                    dont_filter=True,
                )

    def parse_api(self, response: Response):
        site = response.meta["site"]
        site_name = site.get("name", "api")
        keyword = response.meta["keyword"]
        data = response.json()
        results = data.get("results", [])
        if not results:
            return

        image_keys = site.get("image_keys", [])
        thumb_keys = site.get("thumbnail_keys", [])
        page_url_key = site.get("page_url_key")

        for entry in results:
            counter_key = f"{site_name}|{keyword}"
            if self.api_keyword_counts[counter_key] >= self.max_api_results:
                continue

            observation_url = self._resolve_observation_url(entry, page_url_key)
            photos = entry.get("photos", [])
            if not photos:
                continue

            image_urls: List[str] = []
            thumbnails: List[str] = []
            captions: List[str] = []
            metadata_payload: List[Dict[str, Any]] = []

            for photo in photos:
                image_url = self._extract_nested_value(photo, image_keys)
                if not image_url:
                    continue
                high_res = self._upgrade_inaturalist_url(image_url)
                thumb_url = self._extract_nested_value(photo, thumb_keys) or high_res

                image_urls.append(high_res)
                thumbnails.append(thumb_url)
                captions.append(entry.get("species_guess") or entry.get("description"))
                metadata_payload.append(
                    {
                        "license": photo.get("license_code"),
                        "observed_on": entry.get("observed_on"),
                        "location": entry.get("location"),
                        "observation_id": entry.get("id"),
                    }
                )

            if not image_urls:
                continue

            self.api_keyword_counts[counter_key] += 1

            yield ScraperItem(
                query=keyword,
                image_urls=image_urls,
                thumbnail_urls=thumbnails,
                page_urls=[observation_url] * len(image_urls),
                image_captions=captions,
                source_site=site_name,
                metadata={
                    "site_name": site_name,
                    "api_payload": metadata_payload,
                    "source_url": observation_url,
                },
            )

    def _schedule_commons_requests(self, site: Dict[str, Any]):
        base_url = site.get("base_url")
        search_conf = site.get("search", {})
        base_params = search_conf.get("params", {})
        if not base_url or not base_params:
            self.logger.warning("Commons site '%s' misconfigured; skipping.", site.get("name"))
            return

        max_pages = max(1, int(search_conf.get("max_pages", 1)))
        offset_param = search_conf.get("offset_param", "gsroffset")

        for keyword in self.keywords:
            params = base_params.copy()
            params["gsrsearch"] = keyword

            yield scrapy.Request(
                url=f"{base_url}?{urlencode(params)}",
                callback=self.parse_commons,
                meta={
                    "site": site,
                    "keyword": keyword,
                    "base_url": base_url,
                    "base_params": base_params,
                    "offset_param": offset_param,
                    "pages_sent": 1,
                    "max_pages": max_pages,
                },
                dont_filter=True,
            )

    def parse_commons(self, response: Response):
        site = response.meta["site"]
        site_name = site.get("name", "commons")
        keyword = response.meta["keyword"]
        base_url = response.meta["base_url"]
        base_params = response.meta["base_params"]
        max_pages = response.meta.get("max_pages", 1)
        pages_sent = response.meta.get("pages_sent", 1)
        offset_param = response.meta.get("offset_param", "gsroffset")

        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        limit = min(site.get("max_results_per_keyword", self.max_api_results), self.max_api_results)
        counter_key = f"{site_name}|{keyword}"

        for page in pages:
            if self.api_keyword_counts[counter_key] >= limit:
                break

            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            info = imageinfo[0]
            image_url = info.get("url")
            if not image_url:
                continue
            thumbnail = info.get("thumburl") or image_url

            extmetadata = info.get("extmetadata", {})
            caption = self._extract_extmetadata_value(extmetadata, ["ObjectName", "ImageDescription", "Categories"])
            license_name = self._extract_extmetadata_value(extmetadata, ["LicenseShortName"])
            attribution = self._extract_extmetadata_value(extmetadata, ["Artist"])
            page_title = page.get("title")
            page_url = self._build_commons_page_url(page_title)

            metadata_payload = {
                "width": info.get("width"),
                "height": info.get("height"),
                "mime": info.get("mime"),
                "license": license_name,
                "attribution": attribution,
                "commons_title": page_title,
            }

            self.api_keyword_counts[counter_key] += 1

            yield ScraperItem(
                query=keyword,
                image_urls=[image_url],
                thumbnail_urls=[thumbnail],
                page_urls=[page_url],
                image_captions=[caption],
                source_site=site_name,
                metadata=metadata_payload,
            )

        if self.api_keyword_counts[counter_key] >= limit:
            return

        if pages_sent >= max_pages:
            return

        cont = data.get("continue")
        if not cont:
            return

        params = base_params.copy()
        params["gsrsearch"] = keyword
        params.update(cont)

        next_meta = dict(response.meta)
        next_meta["pages_sent"] = pages_sent + 1

        yield scrapy.Request(
            url=f"{base_url}?{urlencode(params)}",
            callback=self.parse_commons,
            meta=next_meta,
            dont_filter=True,
        )

    def _schedule_gbif_requests(self, site: Dict[str, Any]):
        match_url = site.get("species_match_url")
        if not match_url:
            self.logger.error("Site '%s' missing species_match_url; skipping.", site.get("name"))
            return

        query_conf = site.get("query", {})

        for keyword in self.keywords:
            search_term = site.get("keyword_overrides", {}).get(keyword, keyword)
            params = {"name": search_term}

            yield scrapy.Request(
                url=f"{match_url}?{urlencode(params)}",
                callback=self.parse_gbif_species_match,
                meta={
                    "site": site,
                    "keyword": keyword,
                    "search_term": search_term,
                    "query_conf": query_conf,
                },
                dont_filter=True,
            )

    def parse_gbif_species_match(self, response: Response):
        site = response.meta["site"]
        keyword = response.meta["keyword"]
        search_term = response.meta["search_term"]
        query_conf = response.meta.get("query_conf", {})
        site_name = site.get("name", "gbif")

        data = response.json()
        usage_key = (
            data.get("usageKey")
            or data.get("speciesKey")
            or data.get("acceptedUsageKey")
            or data.get("acceptedKey")
        )

        base_url = site.get("base_url")
        if not base_url:
            self.logger.error("Site '%s' missing base_url for occurrence search.", site_name)
            return

        params_template = query_conf.get("params", {}).copy()
        params_template.setdefault("limit", query_conf.get("per_page", params_template.get("limit", 50)))
        params_template.pop("offset", None)

        per_page = int(params_template.get("limit", 50))
        max_pages = max(1, int(query_conf.get("max_pages", 1)))
        limit_per_keyword = min(site.get("max_results_per_keyword", self.max_api_results), self.max_api_results)

        if usage_key:
            param_name = query_conf.get("param", "taxon_key")
            params_template[param_name] = usage_key
            mode = "taxon"
        else:
            self.logger.warning(
                "GBIF species match failed for '%s' (search term '%s'); falling back to text search.",
                keyword,
                search_term,
            )
            params_template["q"] = search_term
            mode = "q"

        params = params_template.copy()
        params["offset"] = 0

        meta = {
            "site": site,
            "keyword": keyword,
            "params_template": params_template,
            "per_page": per_page,
            "page_index": 1,
            "max_pages": max_pages,
            "offset": 0,
            "base_url": base_url,
            "limit_per_keyword": limit_per_keyword,
            "mode": mode,
        }

        yield scrapy.Request(
            url=f"{base_url}?{urlencode(params)}",
            callback=self.parse_gbif_occurrence,
            meta=meta,
            dont_filter=True,
        )

    def parse_gbif_occurrence(self, response: Response):
        site = response.meta["site"]
        site_name = site.get("name", "gbif")
        keyword = response.meta["keyword"]
        params_template = response.meta["params_template"]
        per_page = response.meta["per_page"]
        page_index = response.meta["page_index"]
        max_pages = response.meta["max_pages"]
        offset = response.meta.get("offset", 0)
        base_url = response.meta["base_url"]
        limit_per_keyword = response.meta["limit_per_keyword"]

        data = response.json()
        results = data.get("results", [])

        counter_key = f"{site_name}|{keyword}"
        remaining = limit_per_keyword - self.api_keyword_counts[counter_key]
        if remaining <= 0:
            return

        allowed_media_domains = set(site.get("media_domains", []))

        for occurrence in results:
            remaining = limit_per_keyword - self.api_keyword_counts[counter_key]
            if remaining <= 0:
                break

            images = []
            thumbnails = []
            captions = []
            page_urls = []
            metadata_payload = []

            for media in occurrence.get("media", []):
                identifier = media.get("identifier")
                if not identifier:
                    continue
                host = urlparse(identifier).netloc
                if allowed_media_domains and host not in allowed_media_domains:
                    continue
                images.append(identifier)
                thumbnails.append(identifier)
                captions.append(media.get("title") or occurrence.get("scientificName"))
                page_urls.append(media.get("references") or occurrence.get("references"))
                metadata_payload.append(
                    {
                        "license": media.get("license"),
                        "creator": media.get("creator"),
                        "publisher": media.get("publisher"),
                        "rights_holder": media.get("rightsHolder"),
                        "occurrence_id": occurrence.get("occurrenceID"),
                        "dataset_key": occurrence.get("datasetKey"),
                    }
                )

            if not images:
                continue

            if len(images) > remaining:
                images = images[:remaining]
                thumbnails = thumbnails[:remaining]
                captions = captions[:remaining]
                page_urls = page_urls[:remaining]
                metadata_payload = metadata_payload[:remaining]

            self.api_keyword_counts[counter_key] += len(images)

            yield ScraperItem(
                query=keyword,
                image_urls=images,
                thumbnail_urls=thumbnails,
                page_urls=page_urls,
                image_captions=captions,
                source_site=site_name,
                metadata={
                    "gbif_mode": response.meta.get("mode"),
                    "gbif_offset": offset,
                    "occurrence_count": len(images),
                    "payload": metadata_payload,
                },
            )

        if self.api_keyword_counts[counter_key] >= limit_per_keyword:
            return

        if page_index >= max_pages:
            return

        if not results:
            return

        next_offset = offset + per_page
        params = params_template.copy()
        params["offset"] = next_offset

        next_meta = dict(response.meta)
        next_meta["offset"] = next_offset
        next_meta["page_index"] = page_index + 1

        yield scrapy.Request(
            url=f"{base_url}?{urlencode(params)}",
            callback=self.parse_gbif_occurrence,
            meta=next_meta,
            dont_filter=True,
        )

    # --- helper methods ---
    def _extract_clean_text(self, selector: scrapy.Selector, css: Optional[str]) -> Optional[str]:
        if not css:
            return None
        text = selector.css(css).get()
        if text:
            return " ".join(text.split())
        return None

    def _extract_clean_attr(self, selector: scrapy.Selector, css: Optional[str]) -> Optional[str]:
        if not css:
            return None
        value = selector.css(css).get()
        if value:
            return value.strip()
        return None

    def _extract_first_available(self, selector: scrapy.Selector, css_list: List[str]) -> Optional[str]:
        for css in css_list:
            value = self._extract_clean_attr(selector, css)
            if value:
                return value
        return None

    def _extract_nested_value(self, obj: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = obj.get(key)
            if value:
                return value
        return None

    def _resolve_observation_url(self, entry: Dict[str, Any], page_url_key: Optional[str]) -> Optional[str]:
        if page_url_key and entry.get(page_url_key):
            return entry[page_url_key]
        obs_id = entry.get("id")
        if obs_id:
            return f"https://www.inaturalist.org/observations/{obs_id}"
        return None

    def _upgrade_inaturalist_url(self, url: str) -> str:
        if "square" in url:
            return url.replace("square", "large")
        return url

    def _extract_extmetadata_value(self, metadata: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, dict):
                text = value.get("value")
            else:
                text = value
            if text:
                return " ".join(str(text).split())
        return None

    def _build_commons_page_url(self, title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        safe_title = title.replace(" ", "_")
        return f"https://commons.wikimedia.org/wiki/{safe_title}"
