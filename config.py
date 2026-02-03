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

# Ticker CSV file (place your CSV with 'tic' column here)
TICKER_CSV_FILE = DATA_DIR / "tickers.csv"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
