import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        
        # Search configuration
        default_terms = 'SBA loans,SBA lending,SBA loan programs,7(a) loan program'
        search_terms_env = os.getenv('SEARCH_TERMS', default_terms)
        
        # Support both comma and semicolon separators for flexibility
        if ',' in search_terms_env:
            terms = [term.strip() for term in search_terms_env.split(',')]
        else:
            terms = [term.strip() for term in search_terms_env.split(';')]
            
        self.SEARCH_TERMS = [term for term in terms if term]  # Remove empty terms
        self.ARTICLE_LIMIT = int(os.getenv('ARTICLE_LIMIT', '10'))
        
        # Additional search configuration
        self.SEARCH_LANG = os.getenv('SEARCH_LANG', 'en')
        self.SEARCH_SORT = os.getenv('SEARCH_SORT', 'relevancy')  # options: relevancy, popularity, publishedAt
        
        # Schedule configuration
        self.SCHEDULE_INTERVAL = int(os.getenv('SCHEDULE_INTERVAL', '60'))  # minutes
        
        # N8N webhook configuration
        self.N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', '')
        
        # NewsAPI configuration
        self.NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
        
        # Request configuration
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.WEBHOOK_MIN_INTERVAL = float(os.getenv('WEBHOOK_MIN_INTERVAL', '5.0'))  # Minimum seconds between webhook calls
