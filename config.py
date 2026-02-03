"""
Configuration settings for the Polymarket First Mention Tracker.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Data storage
DATA_DIR = BASE_DIR / "data"
FIRST_MENTIONS_FILE = DATA_DIR / "first_mentions.json"
PROCESSED_MARKETS_FILE = DATA_DIR / "processed_markets.json"

# Polymarket API
POLYMARKET_API_BASE_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_API_URL = "https://clob.polymarket.com"

# Rate limiting
API_RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# Matching settings
MIN_TICKER_LENGTH = 2  # Minimum ticker length to avoid false positives
EXCLUDE_COMMON_WORDS = {
    "A", "I", "IT", "AT", "ON", "TO", "IN", "IS", "AS", "OR", "AN", "BE", "BY",
    "DO", "GO", "HE", "IF", "ME", "MY", "NO", "OF", "OK", "SO", "UP", "US", "WE",
    "ALL", "AND", "ARE", "BUT", "CAN", "DAY", "DID", "FOR", "GET", "GOT", "HAS",
    "HAD", "HER", "HIM", "HIS", "HOW", "ITS", "LET", "MAY", "NEW", "NOT", "NOW",
    "OLD", "ONE", "OUR", "OUT", "OWN", "SAY", "SEE", "SHE", "THE", "TOO", "TWO",
    "WAY", "WHO", "WHY", "YES", "YET", "YOU", "CEO", "CFO", "COO", "IPO", "SEC",
    "FDA", "FTC", "DOJ", "EPA", "FCC", "NYSE", "ETF", "GDP", "USA", "WIN", "BUY",
    "SELL", "HOLD", "LONG", "SHORT", "CALL", "PUT", "BID", "ASK", "HIGH", "LOW",
    "OPEN", "CLOSE", "WILL", "OVER", "UNDER", "MORE", "LESS", "THAN", "JUST",
    "MOST", "NEXT", "LAST", "FIRST", "BEST", "WORST", "GOOD", "BAD", "TOP",
    "REAL", "TRUE", "FALSE", "RISE", "FALL", "DROP", "GAIN", "LOSS", "PEAK",
}

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
