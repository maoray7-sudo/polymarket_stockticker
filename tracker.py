"""
First Mention Tracker.

Core logic for tracking when US listed firms are first mentioned on Polymarket.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator, List, Optional, Tuple

from polymarket_client import PolymarketClient, PolymarketMarket, get_polymarket_client
from storage import FirstMention, MentionStorage, get_storage
from us_stocks import Stock, USStockDatabase, get_stock_database


@dataclass
class ScanResult:
    """Result of scanning markets for stock mentions."""
    markets_scanned: int
    new_first_mentions: int
    total_mentions_found: int
    skipped_markets: int
    errors: int


class FirstMentionTracker:
    """
    Tracks first mentions of US listed firms on Polymarket.

    This class coordinates between the stock database, Polymarket client,
    and storage to identify and record first mentions.
    """

    def __init__(
        self,
        stock_db: Optional[USStockDatabase] = None,
        polymarket_client: Optional[PolymarketClient] = None,
        storage: Optional[MentionStorage] = None,
    ):
        self.stock_db = stock_db or get_stock_database()
        self.client = polymarket_client or get_polymarket_client()
        self.storage = storage or get_storage()

    def scan_market(self, market: PolymarketMarket) -> List[Tuple[Stock, str]]:
        """
        Scan a single market for stock mentions in the question only.

        Args:
            market: The market to scan

        Returns:
            List of (Stock, matched_text) tuples found in the market question
        """
        # Only search in the question field, not description or other fields
        return self.stock_db.find_mentions(market.question)

    def process_market(
        self,
        market: PolymarketMarket,
        force: bool = False
    ) -> List[FirstMention]:
        """
        Process a single market and record any first mentions.

        Args:
            market: The market to process
            force: If True, process even if already processed

        Returns:
            List of new first mentions found
        """
        if not force and self.storage.is_market_processed(market.id):
            return []

        mentions_found = []
        stock_mentions = self.scan_market(market)

        for stock, matched_text in stock_mentions:
            mention = FirstMention(
                ticker=stock.ticker,
                company_name=stock.company_name,
                first_mention_date=market.created_at,
                market_id=market.id,
                market_question=market.question,
                market_description=market.description[:500] if market.description else "",
                market_url=market.url,
                matched_text=matched_text,
                market_created_at=market.created_at,
                exchange=stock.exchange,
                sector=stock.sector,
                industry=stock.industry,
            )

            if self.storage.add_first_mention(mention):
                mentions_found.append(mention)

        self.storage.mark_market_processed(market.id)
        return mentions_found

    def scan_all_markets(
        self,
        max_markets: Optional[int] = None,
        include_closed: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        save_interval: int = 100,
    ) -> ScanResult:
        """
        Scan all Polymarket markets for stock mentions.

        Args:
            max_markets: Maximum number of markets to scan
            include_closed: Whether to include closed markets
            progress_callback: Optional callback(scanned, total, message)
            save_interval: How often to save progress (every N markets)

        Returns:
            ScanResult with statistics about the scan
        """
        result = ScanResult(
            markets_scanned=0,
            new_first_mentions=0,
            total_mentions_found=0,
            skipped_markets=0,
            errors=0,
        )

        try:
            for market in self.client.get_all_markets(
                max_markets=max_markets,
                include_closed=include_closed
            ):
                try:
                    if self.storage.is_market_processed(market.id):
                        result.skipped_markets += 1
                        continue

                    new_mentions = self.process_market(market)
                    result.markets_scanned += 1
                    result.new_first_mentions += len(new_mentions)
                    result.total_mentions_found += len(self.scan_market(market))

                    if progress_callback:
                        progress_callback(
                            result.markets_scanned,
                            max_markets or 0,
                            f"Processing: {market.question[:50]}..."
                        )

                    # Periodic save
                    if result.markets_scanned % save_interval == 0:
                        self.storage.save()
                        self.storage.last_processed_date = datetime.now()

                except Exception as e:
                    result.errors += 1
                    print(f"Error processing market {market.id}: {e}")
                    continue

        finally:
            # Final save
            self.storage.save()
            self.storage.last_processed_date = datetime.now()

        return result

    def scan_new_markets(
        self,
        since: Optional[datetime] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> ScanResult:
        """
        Scan only new markets since the last scan.

        Args:
            since: Start date (defaults to last processed date)
            progress_callback: Optional progress callback

        Returns:
            ScanResult with statistics
        """
        if since is None:
            since = self.storage.last_processed_date

        if since is None:
            # No previous scan, scan all
            return self.scan_all_markets(progress_callback=progress_callback)

        result = ScanResult(
            markets_scanned=0,
            new_first_mentions=0,
            total_mentions_found=0,
            skipped_markets=0,
            errors=0,
        )

        try:
            for market in self.client.get_markets_by_date_range(since):
                try:
                    if self.storage.is_market_processed(market.id):
                        result.skipped_markets += 1
                        continue

                    new_mentions = self.process_market(market)
                    result.markets_scanned += 1
                    result.new_first_mentions += len(new_mentions)
                    result.total_mentions_found += len(self.scan_market(market))

                    if progress_callback:
                        progress_callback(
                            result.markets_scanned,
                            0,
                            f"Processing: {market.question[:50]}..."
                        )

                except Exception as e:
                    result.errors += 1
                    print(f"Error processing market {market.id}: {e}")
                    continue

        finally:
            self.storage.save()
            self.storage.last_processed_date = datetime.now()

        return result

    def search_stock_markets(
        self,
        ticker: str,
        limit: int = 50
    ) -> List[PolymarketMarket]:
        """
        Search for markets mentioning a specific stock.

        Args:
            ticker: Stock ticker to search for
            limit: Maximum results to return

        Returns:
            List of markets mentioning the stock
        """
        stock = self.stock_db.get_stock(ticker.upper())
        if not stock:
            return []

        # Search by both ticker and company name
        markets = []
        seen_ids = set()

        # Search by ticker
        ticker_results = self.client.search_markets(stock.ticker, limit=limit // 2)
        for market in ticker_results:
            if market.id not in seen_ids:
                markets.append(market)
                seen_ids.add(market.id)

        # Search by company name
        name_results = self.client.search_markets(stock.company_name, limit=limit // 2)
        for market in name_results:
            if market.id not in seen_ids:
                markets.append(market)
                seen_ids.add(market.id)

        return markets[:limit]

    def get_first_mention(self, ticker: str) -> Optional[FirstMention]:
        """Get the first mention for a specific stock."""
        return self.storage.get_first_mention(ticker.upper())

    def get_all_first_mentions(self) -> List[FirstMention]:
        """Get all tracked first mentions."""
        return self.storage.get_all_first_mentions()

    def get_recent_first_mentions(
        self,
        days: int = 30
    ) -> List[FirstMention]:
        """Get first mentions from the last N days."""
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)
        return self.storage.get_mentions_by_date_range(start_date)

    def get_statistics(self) -> dict:
        """Get tracking statistics."""
        return {
            "storage": self.storage.get_statistics(),
            "stock_database_size": len(self.stock_db),
        }

    def find_untracked_stocks(
        self,
        text: str
    ) -> List[str]:
        """
        Find potential stock tickers in text that aren't in our database.

        This can help identify stocks that might need to be added to the database.
        """
        import re

        # Find all potential ticker-like patterns
        potential_tickers = set(re.findall(r'\b[A-Z]{2,5}\b', text.upper()))

        # Filter out known stocks and common words
        from config import EXCLUDE_COMMON_WORDS
        known_tickers = self.stock_db.get_all_tickers()

        untracked = [
            ticker for ticker in potential_tickers
            if ticker not in known_tickers and ticker not in EXCLUDE_COMMON_WORDS
        ]

        return sorted(untracked)


def create_tracker() -> FirstMentionTracker:
    """Create a new FirstMentionTracker instance with default dependencies."""
    return FirstMentionTracker()
