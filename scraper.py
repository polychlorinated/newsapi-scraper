import trafilatura
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger('news_scraper')

class ArticleScraper:
    def __init__(self):
        self.downloaded_cache = {}

    def _download_content(self, url: str) -> Optional[str]:
        """Download URL content with retries"""
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                downloaded = trafilatura.fetch_url(url)
                
                if downloaded:
                    return downloaded
                    
            except Exception as e:
                logger.error(f"Error downloading content: {str(e)}")
                    
            current_try += 1
            if current_try < max_retries:
                time.sleep(2 ** current_try)  # Exponential backoff
                
        return None

    def enrich_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches an article by scraping its full content from the URL.
        Returns the article with additional content if successful.
        """
        url = article.get('url')
        if not url:
            logger.warning("Article missing URL, skipping content enrichment")
            return article

        try:
            # Check cache first
            if url in self.downloaded_cache:
                logger.debug(f"Using cached content for {url}")
                full_content = self.downloaded_cache[url]
            else:
                logger.debug(f"Fetching full content from {url}")
                downloaded = self._download_content(url)
                full_content = trafilatura.extract(downloaded, include_comments=False, 
                                                include_tables=False, 
                                                include_images=False,
                                                favor_precision=True)
                if full_content:
                    self.downloaded_cache[url] = full_content

            if full_content:
                enriched_article = article.copy()
                enriched_article.update({
                    'full_content': full_content,
                    'scraped_at': datetime.now().isoformat(),
                    'scraping_success': True
                })
                logger.info(f"Successfully enriched article: {article.get('title', '')}")
                return enriched_article
            else:
                logger.warning(f"Failed to extract content from {url}")
                return {**article, 'scraping_success': False}

        except Exception as e:
            logger.error(f"Error enriching article from {url}: {str(e)}")
            return {**article, 'scraping_success': False}
