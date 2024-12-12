from newsapi.newsapi_client import NewsApiClient
from typing import List, Dict, Any, Set, Optional
import logging
import json
import os
from datetime import datetime, timedelta
import time
from functools import lru_cache
import requests
from requests.exceptions import RequestException
from scraper import ArticleScraper
from difflib import SequenceMatcher
logger = logging.getLogger('news_scraper')



class NewsAPIClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.client = NewsApiClient(api_key=api_key)
        self.timeout = timeout
        self._request_interval = 1.0  # Minimum seconds between API requests
        self._last_request_time = 0
        
        # Initialize caches
        self._seen_articles = set()
        self._seen_titles = set()
        self._content_hashes = set()
        self._cache_file = 'seen_articles_cache.json'
        self._load_cache()
        self.scraper = ArticleScraper()
        
    def _load_cache(self):
        """Load cached article data from file"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    cache = json.load(f)
                self._seen_articles = set(cache.get('urls', []))
                self._seen_titles = set(cache.get('titles', []))
                self._content_hashes = set(cache.get('content_hashes', []))
                logger.debug(f"Loaded {len(self._seen_articles)} cached articles")
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
            self._seen_articles = set()
            self._seen_titles = set()
            self._content_hashes = set()

    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retries"""
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                response = requests.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Request failed with status {response.status_code}")
                    
            except RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                    
            current_try += 1
            if current_try < max_retries:
                time.sleep(2 ** current_try)  # Exponential backoff
                
        return None
            
    def _save_cache(self):
        """Save article cache to file"""
        try:
            cache = {
                'urls': list(self._seen_articles),
                'titles': list(self._seen_titles),
                'content_hashes': list(self._content_hashes),
                'last_updated': datetime.now().isoformat()
            }
            with open(self._cache_file, 'w') as f:
                json.dump(cache, f)
            logger.debug("Saved article cache to file")
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")

    def _get_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two text strings"""
        return SequenceMatcher(None, text1, text2).ratio()
        
    def _is_similar_content(self, content: str, similarity_threshold: float = 0.8) -> bool:
        """Check if content is similar to any previously seen article content"""
        if not content:
            return False
            
        # Hash the content for faster comparison
        content_hash = hash(content)
        if content_hash in self._content_hashes:
            logger.debug("Exact content match found (hash collision)")
            return True
            
        # Only check similarity with the most recent articles to allow more fresh content
        recent_hashes = list(self._content_hashes)[-10:]  # Reduced from 15 to 10 articles
        
        # Check similarity with recent articles
        for seen_hash in recent_hashes:
            similarity = self._get_content_similarity(content, str(seen_hash))
            if similarity > similarity_threshold:  # Increased threshold for stricter duplicate detection
                logger.debug(f"Similar content found (similarity: {similarity:.2f})")
                return True
                
        logger.debug(f"Content is sufficiently different from recent articles")
        return False

    def _get_title_words(self, title: str) -> set:
        """Get set of significant words from title"""
        # Remove common words and punctuation
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = set(word.lower() for word in title.split() if word.lower() not in common_words)
        return words

    def _is_similar_title(self, title1: str, title2: str, similarity_threshold: float = 0.6) -> bool:
        """Check if two titles are similar based on word overlap"""
        if title1 == title2:
            logger.debug(f"Exact title match found: {title1}")
            return True
            
        words1 = self._get_title_words(title1)
        words2 = self._get_title_words(title2)
        
        if not words1 or not words2:
            return False
            
        intersection = len(words1.intersection(words2))
        shorter_len = min(len(words1), len(words2))
        similarity = intersection / shorter_len
        
        if similarity >= similarity_threshold:
            logger.debug(f"Similar titles found (similarity: {similarity:.2f}):\n  Title 1: {title1}\n  Title 2: {title2}")
            return True
        return False
        
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._request_interval:
            time.sleep(self._request_interval - time_since_last_request)
        self._last_request_time = time.time()

    @lru_cache(maxsize=100)
    def _is_relevant_article(self, title: str, description: str, search_term: str) -> bool:
        """
        Check if an article is relevant to the search term
        Uses keyword matching with improved flexible criteria
        """
        # Handle special cases for SBA-related searches
        text = f"{title} {description}".lower()
        search_phrases = [phrase.strip().lower() for phrase in search_term.split(',')]
        
        # Log the article we're checking
        logger.info(f"Analyzing relevance for article: {title}")
        logger.debug(f"Search phrases: {search_phrases}")
        
        # Temporarily relaxed relevance criteria for testing exports
        # Define broader keywords for testing
        business_related_terms = {'business', 'loan', 'lending', 'bank', 'finance', 
                                'sba', 'small business', 'funding', 'capital'}
        
        # Check for business-related terms with relaxed matching
        matched_terms = [term for term in business_related_terms if term in text.lower()]
        if matched_terms:
            logger.info(f"Found business-related terms in article: {matched_terms}")
            return True
            
        # Check for any search phrase words
        search_words = set(word.lower() for phrase in search_phrases 
                         for word in phrase.split())
        if any(word in text.lower() for word in search_words):
            logger.info(f"Found search term match in article")
            return True
        
        # Check for partial matches using individual words
        # Exclude common stop words to focus on meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        search_words = set()
        for phrase in search_phrases:
            words = [word.strip() for word in phrase.split() 
                    if word.strip() and word.strip().lower() not in stop_words]
            search_words.update(words)
        
        if not search_words:
            logger.debug("No valid search words after filtering stop words")
            return False
            
        # Count matches and calculate relevance score
        matches = []
        for word in search_words:
            if word in text:
                matches.append(word)
                
        relevance_score = len(matches) / len(search_words)
        
        # More lenient threshold (15%) with additional context logging
        if relevance_score >= 0.15:
            logger.info(f"Article '{title}' matches keywords: {matches} (score: {relevance_score:.2f})")
            return True
            
        logger.debug(f"Article below relevance threshold ({relevance_score:.2f}): {title}")
        return False

    def fetch_articles(self, search_term: str, article_limit: int) -> List[Dict[str, Any]]:
        """
        Fetch articles from NewsAPI for a given search term with improved handling
        """
        try:
            self._rate_limit()
            
            # Calculate date range (last 7 days for more content)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)

            response = self.client.get_everything(
                q=search_term,
                language='en',
                sort_by='publishedAt',  # Get newest articles first
                from_param=from_date.strftime('%Y-%m-%d'),
                to=to_date.strftime('%Y-%m-%d'),
                page_size=min(article_limit * 5, 100)  # Fetch more articles for better filtering
            )

            if not response.get('articles'):
                logger.warning(f"No articles found for search term: {search_term}")
                # Try with top headlines as fallback
                response = self.client.get_top_headlines(
                    q=search_term,
                    language='en',
                    page_size=min(article_limit * 2, 20)
                )

            if not response.get('articles'):
                logger.warning(f"No articles found for search term: {search_term}")
                return []

            articles = []
            for article in response['articles']:
                title = article['title']
                url = article['url']
                content = article.get('content', '')
                
                # Skip if it's not test data and URL already seen
                if url in self._seen_articles and not article.get('is_test_data', False):
                    logger.debug(f"Skipping duplicate URL: {title} (URL: {url})")
                    continue
                
                # Skip if similar title exists (unless test data)
                if not article.get('is_test_data', False) and any(self._is_similar_title(title, seen_title) for seen_title in self._seen_titles):
                    logger.debug(f"Skipping article with similar title: {title}")
                    logger.debug("Similar titles found in cache")
                    continue
                    
                # Skip if similar content exists (unless test data)
                if not article.get('is_test_data', False) and content and self._is_similar_content(content):
                    logger.debug(f"Skipping article with similar content: {title}")
                    logger.debug("Content similarity threshold exceeded")
                    continue

                # Check relevance
                if not self._is_relevant_article(
                    article['title'], 
                    article.get('description', ''), 
                    search_term
                ):
                    logger.debug(f"Skipping irrelevant article: {article['title']}")
                    continue

                # Prepare text for analysis
                full_text = f"{article['title']} {article.get('description', '')} {article.get('content', '')}"
                
                processed_article = {
                    'title': article['title'],
                    'url': article['url'],
                    'source': article['source']['name'],
                    'date': article['publishedAt'],
                    'search_term': search_term,
                    'description': article.get('description', ''),
                    'content': article.get('content', '')
                }
                
                # Enrich with full content from website
                enriched_article = self.scraper.enrich_article(processed_article)
                
                # Cache article unless it's test data
                if not processed_article.get('is_test_data', False):
                    # Add to cache only if it's not already seen
                    if article['url'] not in self._seen_articles:
                        self._seen_articles.add(article['url'])
                        self._seen_titles.add(article['title'])
                        if content:
                            self._content_hashes.add(hash(content))
                        logger.debug(f"Cached new article: {processed_article['title']}")
                else:
                    logger.debug(f"Skipping cache for test article: {processed_article['title']}")
                
                articles.append(enriched_article)
                logger.debug(f"Found article: {processed_article['title']}")

                if len(articles) >= article_limit:
                    logger.debug(f"Reached article limit ({article_limit}), stopping search")
                    break
                    
            # Save updated cache
            self._save_cache()

            logger.info(f"Successfully fetched {len(articles)} articles for search term: {search_term}")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch articles for {search_term}: {str(e)}")
            return []
