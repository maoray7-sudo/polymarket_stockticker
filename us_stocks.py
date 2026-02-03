"""
US Stock Ticker Database Module.

Loads stock tickers from a user-provided CSV file.
Only matches tickers in parentheses format like (TSLA).
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from config import DATA_DIR


@dataclass
class Stock:
    """Represents a US listed stock."""
    ticker: str
    company_name: str = ""
    exchange: str = ""
    sector: str = ""
    industry: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        return cls(
            ticker=data["ticker"],
            company_name=data.get("company_name", ""),
            exchange=data.get("exchange", ""),
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
        )


class USStockDatabase:
    """
    Database of US listed stocks.

    Loads tickers from a CSV file and only matches tickers
    that appear in parentheses format like (TSLA).
    """

    # Default CSV file path - user should place their CSV here
    DEFAULT_CSV_FILE = DATA_DIR / "tickers.csv"

    def __init__(self, csv_file: Optional[Path] = None):
        """
        Initialize the stock database.

        Args:
            csv_file: Path to CSV file with 'tic' column.
                      If None, uses default path: data/tickers.csv
        """
        self.csv_file = csv_file or self.DEFAULT_CSV_FILE
        self.stocks: Dict[str, Stock] = {}
        self._load_from_csv()

    def _load_from_csv(self):
        """Load stock tickers from CSV file."""
        if not self.csv_file.exists():
            print(f"Warning: CSV file not found at {self.csv_file}")
            print("Please place your tickers CSV file with 'tic' column at this location.")
            print("Or specify a custom path when creating the database.")
            return

        try:
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Find the ticker column (case-insensitive)
                fieldnames = reader.fieldnames or []
                tic_column = None
                for col in fieldnames:
                    if col.lower() == "tic" or col.lower() == "ticker":
                        tic_column = col
                        break

                if not tic_column:
                    print(f"Error: CSV file must have a 'tic' or 'ticker' column.")
                    print(f"Found columns: {fieldnames}")
                    return

                # Load tickers
                for row in reader:
                    ticker = row.get(tic_column, "").strip().upper()
                    if ticker:
                        # Get optional company name if available
                        company_name = (
                            row.get("company_name", "") or
                            row.get("name", "") or
                            row.get("comnam", "") or
                            ""
                        ).strip()

                        stock = Stock(
                            ticker=ticker,
                            company_name=company_name,
                        )
                        self.stocks[ticker] = stock

            print(f"Loaded {len(self.stocks)} tickers from {self.csv_file}")

        except Exception as e:
            print(f"Error loading CSV file: {e}")

    def get_stock(self, ticker: str) -> Optional[Stock]:
        """Get stock by ticker symbol."""
        return self.stocks.get(ticker.upper())

    def find_mentions(self, text: str) -> List[Tuple[Stock, str]]:
        """
        Find all stock mentions in the format (TICKER) in the given text.

        Only matches tickers that:
        1. Are enclosed in parentheses like (TSLA)
        2. Exist in our ticker database

        Args:
            text: Text to search for ticker mentions

        Returns:
            List of tuples (Stock, matched_text) found in the text
        """
        if not text:
            return []

        mentions = []
        seen_tickers = set()

        # Pattern to match tickers in parentheses: (TICKER)
        # Matches 1-5 uppercase letters inside parentheses
        pattern = r'\(([A-Z]{1,5})\)'

        matches = re.findall(pattern, text.upper())

        for ticker in matches:
            if ticker in self.stocks and ticker not in seen_tickers:
                matched_text = f"({ticker})"
                mentions.append((self.stocks[ticker], matched_text))
                seen_tickers.add(ticker)

        return mentions

    def get_all_tickers(self) -> Set[str]:
        """Get all ticker symbols in the database."""
        return set(self.stocks.keys())

    def get_all_stocks(self) -> List[Stock]:
        """Get all stocks in the database."""
        return list(self.stocks.values())

    def add_ticker(self, ticker: str, company_name: str = ""):
        """Add a single ticker to the database."""
        ticker = ticker.upper().strip()
        if ticker:
            self.stocks[ticker] = Stock(ticker=ticker, company_name=company_name)

    def __len__(self) -> int:
        return len(self.stocks)

    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in self.stocks


# Singleton instance
_db_instance: Optional[USStockDatabase] = None


def get_stock_database(csv_file: Optional[Path] = None) -> USStockDatabase:
    """
    Get the stock database instance.

    Args:
        csv_file: Optional path to CSV file with 'tic' column.
                  Only used on first call to set the CSV path.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = USStockDatabase(csv_file)
    return _db_instance


def reset_database():
    """Reset the singleton database instance (useful for testing)."""
    global _db_instance
    _db_instance = None
