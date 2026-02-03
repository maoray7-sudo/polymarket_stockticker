"""
Polymarket API Client.

Provides methods to fetch market data from Polymarket's APIs.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import requests

from config import (
    API_RATE_LIMIT_DELAY,
    POLYMARKET_API_BASE_URL,
    POLYMARKET_CLOB_API_URL,
)


@dataclass
class PolymarketMarket:
    """Represents a Polymarket prediction market."""
    id: str
    condition_id: str
    question: str
    description: str
    outcomes: List[str]
    outcome_prices: List[float]
    volume: float
    liquidity: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime
    closed: bool
    resolved: bool
    category: str
    tags: List[str]
    slug: str
    image: str
    url: str

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "PolymarketMarket":
        """Create a PolymarketMarket from API response data."""
        # Parse dates
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                # Handle various date formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                ]:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                return None
            except Exception:
                return None

        # Extract outcome prices
        outcome_prices = []
        if "outcomePrices" in data:
            try:
                prices = data["outcomePrices"]
                if isinstance(prices, str):
                    # Parse JSON string
                    import json
                    prices = json.loads(prices)
                outcome_prices = [float(p) for p in prices]
            except (ValueError, TypeError):
                pass

        # Extract outcomes
        outcomes = data.get("outcomes", [])
        if isinstance(outcomes, str):
            try:
                import json
                outcomes = json.loads(outcomes)
            except (ValueError, TypeError):
                outcomes = []

        # Build URL
        slug = data.get("slug", data.get("market_slug", ""))
        url = f"https://polymarket.com/event/{slug}" if slug else ""

        # Parse created_at - use multiple possible field names
        created_at_str = (
            data.get("createdAt") or
            data.get("created_at") or
            data.get("startDate") or
            data.get("start_date_iso")
        )
        created_at = parse_date(created_at_str) or datetime.now()

        return cls(
            id=str(data.get("id", data.get("condition_id", ""))),
            condition_id=str(data.get("conditionId", data.get("condition_id", ""))),
            question=data.get("question", data.get("title", "")),
            description=data.get("description", ""),
            outcomes=outcomes,
            outcome_prices=outcome_prices,
            volume=float(data.get("volume", data.get("volume24hr", 0)) or 0),
            liquidity=float(data.get("liquidity", 0) or 0),
            start_date=parse_date(data.get("startDate", data.get("start_date_iso"))),
            end_date=parse_date(data.get("endDate", data.get("end_date_iso"))),
            created_at=created_at,
            closed=bool(data.get("closed", False)),
            resolved=bool(data.get("resolved", False)),
            category=data.get("category", data.get("groupItemTitle", "")),
            tags=data.get("tags", []) if isinstance(data.get("tags"), list) else [],
            slug=slug,
            image=data.get("image", ""),
            url=url,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "condition_id": self.condition_id,
            "question": self.question,
            "description": self.description,
            "outcomes": self.outcomes,
            "outcome_prices": self.outcome_prices,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed": self.closed,
            "resolved": self.resolved,
            "category": self.category,
            "tags": self.tags,
            "slug": self.slug,
            "image": self.image,
            "url": self.url,
        }

    def get_searchable_text(self) -> str:
        """Get all text content that should be searched for mentions."""
        parts = [
            self.question,
            self.description,
            self.category,
            " ".join(self.tags),
            " ".join(self.outcomes),
        ]
        return " ".join(filter(None, parts))


class PolymarketClient:
    """Client for interacting with Polymarket APIs."""

    def __init__(self, rate_limit_delay: float = API_RATE_LIMIT_DELAY):
        self.gamma_base_url = POLYMARKET_API_BASE_URL
        self.clob_base_url = POLYMARKET_CLOB_API_URL
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PolymarketStockTracker/1.0",
            "Accept": "application/json",
        })

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GET request with rate limiting and error handling."""
        self._rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
        except ValueError as e:
            print(f"JSON decode error: {e}")
            return None

    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        closed: Optional[bool] = None,
        active: Optional[bool] = None,
        order: str = "createdAt",
        ascending: bool = False,
    ) -> List[PolymarketMarket]:
        """
        Fetch markets from the Gamma API.

        Args:
            limit: Maximum number of markets to fetch (max 100 per request)
            offset: Pagination offset
            closed: Filter by closed status
            active: Filter by active status
            order: Field to order by
            ascending: Sort order

        Returns:
            List of PolymarketMarket objects
        """
        params = {
            "limit": min(limit, 100),
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }

        if closed is not None:
            params["closed"] = str(closed).lower()
        if active is not None:
            params["active"] = str(active).lower()

        url = f"{self.gamma_base_url}/markets"
        data = self._get(url, params)

        if not data:
            return []

        markets = []
        for market_data in data:
            try:
                market = PolymarketMarket.from_api_response(market_data)
                markets.append(market)
            except Exception as e:
                print(f"Error parsing market: {e}")
                continue

        return markets

    def get_market_by_id(self, market_id: str) -> Optional[PolymarketMarket]:
        """Fetch a single market by ID."""
        url = f"{self.gamma_base_url}/markets/{market_id}"
        data = self._get(url)

        if not data:
            return None

        try:
            return PolymarketMarket.from_api_response(data)
        except Exception as e:
            print(f"Error parsing market: {e}")
            return None

    def get_market_by_slug(self, slug: str) -> Optional[PolymarketMarket]:
        """Fetch a single market by slug."""
        url = f"{self.gamma_base_url}/markets"
        params = {"slug": slug}
        data = self._get(url, params)

        if not data or len(data) == 0:
            return None

        try:
            return PolymarketMarket.from_api_response(data[0])
        except Exception as e:
            print(f"Error parsing market: {e}")
            return None

    def search_markets(
        self,
        query: str,
        limit: int = 100
    ) -> List[PolymarketMarket]:
        """
        Search markets by text query.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching markets
        """
        # The Gamma API supports text search
        url = f"{self.gamma_base_url}/markets"
        params = {
            "limit": min(limit, 100),
            "_q": query,  # Text search parameter
        }
        data = self._get(url, params)

        if not data:
            return []

        markets = []
        for market_data in data:
            try:
                market = PolymarketMarket.from_api_response(market_data)
                markets.append(market)
            except Exception as e:
                print(f"Error parsing market: {e}")
                continue

        return markets

    def get_all_markets(
        self,
        max_markets: Optional[int] = None,
        include_closed: bool = True,
    ) -> Iterator[PolymarketMarket]:
        """
        Generator that yields all markets with pagination.

        Args:
            max_markets: Maximum total markets to fetch (None for all)
            include_closed: Whether to include closed markets

        Yields:
            PolymarketMarket objects
        """
        offset = 0
        limit = 100
        total_fetched = 0

        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "order": "createdAt",
                "ascending": "true",  # Oldest first for chronological processing
            }

            if not include_closed:
                params["closed"] = "false"

            url = f"{self.gamma_base_url}/markets"
            data = self._get(url, params)

            if not data or len(data) == 0:
                break

            for market_data in data:
                try:
                    market = PolymarketMarket.from_api_response(market_data)
                    yield market
                    total_fetched += 1

                    if max_markets and total_fetched >= max_markets:
                        return
                except Exception as e:
                    print(f"Error parsing market: {e}")
                    continue

            # Check if we've reached the end
            if len(data) < limit:
                break

            offset += limit

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch events from the Gamma API.
        Events are groupings of related markets.
        """
        url = f"{self.gamma_base_url}/events"
        params = {
            "limit": min(limit, 100),
            "offset": offset,
        }
        data = self._get(url, params)
        return data if data else []

    def get_event_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Fetch a single event by slug."""
        url = f"{self.gamma_base_url}/events"
        params = {"slug": slug}
        data = self._get(url, params)

        if not data or len(data) == 0:
            return None

        return data[0]

    def get_markets_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Iterator[PolymarketMarket]:
        """
        Get markets created within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (defaults to now)

        Yields:
            PolymarketMarket objects created within the range
        """
        if end_date is None:
            end_date = datetime.now()

        for market in self.get_all_markets():
            if market.created_at:
                if start_date <= market.created_at <= end_date:
                    yield market
                elif market.created_at > end_date:
                    # Since we're iterating chronologically, we can stop here
                    break


# Singleton client instance
_client_instance: Optional[PolymarketClient] = None


def get_polymarket_client() -> PolymarketClient:
    """Get the singleton Polymarket client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = PolymarketClient()
    return _client_instance
