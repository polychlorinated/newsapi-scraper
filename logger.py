import logging
from datetime import datetime
import sys
from colorama import Fore, Style, init

init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

def setup_logger():
    logger = logging.getLogger('news_scraper')
    logger.setLevel(logging.DEBUG)

    # Console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # File handler for complete logging
    file_handler = logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    return logger
