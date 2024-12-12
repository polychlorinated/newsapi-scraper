
from apify_client import ApifyClient
import logging
from datetime import datetime
from config import Config
from news_api import NewsAPIClient
from data_exporter import DataExporter
from logger import setup_logger

def main():
    logger = setup_logger()
    config = Config()
    
    # Initialize clients
    news_client = NewsAPIClient(config.NEWSAPI_KEY, config.REQUEST_TIMEOUT)
    data_exporter = DataExporter("apify_exports")
    
    # Process search terms
    all_articles = []
    for search_term in config.SEARCH_TERMS:
        articles = news_client.fetch_articles(search_term, config.ARTICLE_LIMIT)
        all_articles.extend(articles)
        
    # Export results
    if all_articles:
        # Export to dataset
        for article in all_articles:
            print(json.dumps(article))  # Apify auto-captures stdout as dataset items
            
        # Also save as CSV
        export_path = data_exporter.export_to_csv(all_articles)
        if export_path:
            logger.info(f"Exported {len(all_articles)} articles to {export_path}")
    else:
        logger.warning("No articles found to export")

if __name__ == "__main__":
    main()
