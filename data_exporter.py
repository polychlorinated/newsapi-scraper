import os
import csv
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('news_scraper')

class DataExporter:
    def __init__(self, export_dir: str = "exports"):
        """Initialize the data exporter"""
        self.export_dir = export_dir
        self._ensure_export_directory()

    def _ensure_export_directory(self) -> None:
        """Ensure export directory exists and is writable"""
        try:
            os.makedirs(self.export_dir, exist_ok=True)
            # Test write permissions by creating a temporary file
            test_file = os.path.join(self.export_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info(f"Export directory ready: {self.export_dir}")
        except Exception as e:
            logger.error(f"Failed to setup export directory: {str(e)}")
            raise

    def _validate_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """Validate article data before export"""
        if not articles:
            logger.warning("Empty article list provided")
            return False
            
        required_fields = ['title', 'url', 'source', 'date', 'search_term']
        for article in articles:
            missing_fields = [field for field in required_fields if not article.get(field)]
            if missing_fields:
                logger.warning(f"Article missing required fields: {missing_fields}")
                return False
        return True

    def export_to_csv(self, articles: List[Dict[str, Any]], filename: Optional[str] = None) -> Optional[str]:
        """Export articles to CSV file"""
        if not self._validate_articles(articles):
            logger.error("Article validation failed")
            return None

        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"articles_export_{timestamp}.csv"
            
            filepath = os.path.join(self.export_dir, filename)
            
            # Define comprehensive CSV headers with full article details
            headers = [
                'Title', 'Source', 'URL', 'Published Date', 'Search Term',
                'Description', 'Content Preview', 'Full Content', 'Export Date',
                'Scraping Success', 'Processing Timestamp', 'Source Type',
                'Is Enriched', 'Category', 'Content Length', 'Domain',
                'Export Batch', 'Last Updated'
            ]
            
            # Export to temporary file first
            temp_filepath = f"{filepath}.tmp"
            with open(temp_filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for article in articles:
                    # Extract domain from URL
                    domain = article.get('url', '').split('/')[2] if article.get('url', '') else ''
                    
                    # Calculate content length
                    full_content = article.get('full_content', '')
                    content_length = len(full_content) if full_content else 0
                    
                    # Generate export batch ID
                    export_batch = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M')}"
                    
                    writer.writerow({
                        'Title': article.get('title', ''),
                        'Source': article.get('source', ''),
                        'URL': article.get('url', ''),
                        'Published Date': article.get('date', ''),
                        'Search Term': article.get('search_term', ''),
                        'Description': article.get('description', ''),
                        'Content Preview': article.get('content', '')[:500] + '...' if article.get('content', '') else '',
                        'Full Content': full_content,
                        'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Scraping Success': article.get('scraping_success', False),
                        'Processing Timestamp': datetime.now().isoformat(),
                        'Source Type': 'newsapi',
                        'Is Enriched': bool(full_content),
                        'Category': article.get('search_term', '').split(',')[0],
                        'Content Length': content_length,
                        'Domain': domain,
                        'Export Batch': export_batch,
                        'Last Updated': datetime.now().isoformat()
                    })
            
            # Verify temp file exists and has content
            if not os.path.exists(temp_filepath):
                logger.error(f"Failed to create temporary export file: {temp_filepath}")
                return None
                
            if os.path.getsize(temp_filepath) == 0:
                logger.error("Export file is empty")
                os.remove(temp_filepath)
                return None
            
            # Move temporary file to final location
            os.rename(temp_filepath, filepath)
            logger.info(f"Successfully exported {len(articles)} articles to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {str(e)}")
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return None
