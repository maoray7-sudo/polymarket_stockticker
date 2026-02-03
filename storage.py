"""
Data Storage Module.

Handles persistence of first mentions and processed markets.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config import FIRST_MENTIONS_FILE, PROCESSED_MARKETS_FILE


@dataclass
class FirstMention:
    """Represents the first mention of a stock on Polymarket."""
    ticker: str
    company_name: str
    first_mention_date: datetime
    market_id: str
    market_question: str
    market_description: str
    market_url: str
    matched_text: str
    market_created_at: datetime
    exchange: str = ""
    sector: str = ""
    industry: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "first_mention_date": self.first_mention_date.isoformat(),
            "market_id": self.market_id,
            "market_question": self.market_question,
            "market_description": self.market_description,
            "market_url": self.market_url,
            "matched_text": self.matched_text,
            "market_created_at": self.market_created_at.isoformat(),
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FirstMention":
        return cls(
            ticker=data["ticker"],
            company_name=data["company_name"],
            first_mention_date=datetime.fromisoformat(data["first_mention_date"]),
            market_id=data["market_id"],
            market_question=data["market_question"],
            market_description=data.get("market_description", ""),
            market_url=data.get("market_url", ""),
            matched_text=data.get("matched_text", ""),
            market_created_at=datetime.fromisoformat(data["market_created_at"]),
            exchange=data.get("exchange", ""),
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
        )

    def __str__(self) -> str:
        return (
            f"{self.ticker} ({self.company_name}) - "
            f"First mentioned: {self.first_mention_date.strftime('%Y-%m-%d')}\n"
            f"  Market: {self.market_question}\n"
            f"  URL: {self.market_url}"
        )


@dataclass
class MentionStorage:
    """Storage for first mentions and processing state."""
    first_mentions: Dict[str, FirstMention] = field(default_factory=dict)
    processed_market_ids: Set[str] = field(default_factory=set)
    last_processed_date: Optional[datetime] = None

    def __post_init__(self):
        self._load()

    def _load(self):
        """Load data from files."""
        # Load first mentions
        if FIRST_MENTIONS_FILE.exists():
            try:
                with open(FIRST_MENTIONS_FILE, "r") as f:
                    data = json.load(f)
                    for ticker, mention_data in data.get("mentions", {}).items():
                        self.first_mentions[ticker] = FirstMention.from_dict(mention_data)
                    self.last_processed_date = (
                        datetime.fromisoformat(data["last_processed_date"])
                        if data.get("last_processed_date")
                        else None
                    )
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading first mentions: {e}")

        # Load processed markets
        if PROCESSED_MARKETS_FILE.exists():
            try:
                with open(PROCESSED_MARKETS_FILE, "r") as f:
                    data = json.load(f)
                    self.processed_market_ids = set(data.get("processed_ids", []))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading processed markets: {e}")

    def save(self):
        """Save data to files."""
        # Save first mentions
        mentions_data = {
            "mentions": {
                ticker: mention.to_dict()
                for ticker, mention in self.first_mentions.items()
            },
            "last_processed_date": (
                self.last_processed_date.isoformat()
                if self.last_processed_date
                else None
            ),
            "total_mentions": len(self.first_mentions),
        }
        with open(FIRST_MENTIONS_FILE, "w") as f:
            json.dump(mentions_data, f, indent=2)

        # Save processed markets (only save last 10000 to avoid file bloat)
        processed_list = list(self.processed_market_ids)[-10000:]
        processed_data = {
            "processed_ids": processed_list,
            "total_processed": len(self.processed_market_ids),
        }
        with open(PROCESSED_MARKETS_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)

    def add_first_mention(self, mention: FirstMention) -> bool:
        """
        Add a first mention if the ticker hasn't been seen before.

        Returns True if this is a new first mention, False if already exists.
        """
        if mention.ticker in self.first_mentions:
            # Check if this mention is earlier
            existing = self.first_mentions[mention.ticker]
            if mention.market_created_at < existing.market_created_at:
                self.first_mentions[mention.ticker] = mention
                return True
            return False

        self.first_mentions[mention.ticker] = mention
        return True

    def is_market_processed(self, market_id: str) -> bool:
        """Check if a market has already been processed."""
        return market_id in self.processed_market_ids

    def mark_market_processed(self, market_id: str):
        """Mark a market as processed."""
        self.processed_market_ids.add(market_id)

    def get_first_mention(self, ticker: str) -> Optional[FirstMention]:
        """Get the first mention for a ticker."""
        return self.first_mentions.get(ticker.upper())

    def get_all_first_mentions(self) -> List[FirstMention]:
        """Get all first mentions sorted by date."""
        return sorted(
            self.first_mentions.values(),
            key=lambda m: m.first_mention_date
        )

    def get_mentions_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[FirstMention]:
        """Get first mentions within a date range."""
        if end_date is None:
            end_date = datetime.now()

        return [
            mention for mention in self.first_mentions.values()
            if start_date <= mention.first_mention_date <= end_date
        ]

    def get_mentions_by_sector(self, sector: str) -> List[FirstMention]:
        """Get first mentions for a specific sector."""
        return [
            mention for mention in self.first_mentions.values()
            if mention.sector.lower() == sector.lower()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about tracked mentions."""
        if not self.first_mentions:
            return {
                "total_mentions": 0,
                "sectors": {},
                "exchanges": {},
                "date_range": None,
            }

        mentions = list(self.first_mentions.values())

        # Count by sector
        sectors = {}
        for m in mentions:
            sector = m.sector or "Unknown"
            sectors[sector] = sectors.get(sector, 0) + 1

        # Count by exchange
        exchanges = {}
        for m in mentions:
            exchange = m.exchange or "Unknown"
            exchanges[exchange] = exchanges.get(exchange, 0) + 1

        # Date range
        dates = [m.first_mention_date for m in mentions]
        min_date = min(dates)
        max_date = max(dates)

        return {
            "total_mentions": len(mentions),
            "sectors": sectors,
            "exchanges": exchanges,
            "date_range": {
                "earliest": min_date.isoformat(),
                "latest": max_date.isoformat(),
            },
            "processed_markets": len(self.processed_market_ids),
        }

    def export_to_csv(self, filepath: Path) -> int:
        """Export first mentions to CSV file. Returns number of records exported."""
        import csv

        mentions = self.get_all_first_mentions()
        if not mentions:
            return 0

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Ticker",
                "Company Name",
                "First Mention Date",
                "Exchange",
                "Sector",
                "Industry",
                "Market Question",
                "Market URL",
                "Matched Text",
            ])

            for m in mentions:
                writer.writerow([
                    m.ticker,
                    m.company_name,
                    m.first_mention_date.strftime("%Y-%m-%d"),
                    m.exchange,
                    m.sector,
                    m.industry,
                    m.market_question,
                    m.market_url,
                    m.matched_text,
                ])

        return len(mentions)

    def clear(self):
        """Clear all stored data."""
        self.first_mentions.clear()
        self.processed_market_ids.clear()
        self.last_processed_date = None
        self.save()


# Singleton storage instance
_storage_instance: Optional[MentionStorage] = None


def get_storage() -> MentionStorage:
    """Get the singleton storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MentionStorage()
    return _storage_instance
