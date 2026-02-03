"""
US Stock Ticker Database Module.

Provides a database of US listed firms with their tickers and company names.
Supports fetching updated lists from external sources.
"""

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

from config import BASE_DIR, DATA_DIR, EXCLUDE_COMMON_WORDS, MIN_TICKER_LENGTH


@dataclass
class Stock:
    """Represents a US listed stock."""
    ticker: str
    company_name: str
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
            company_name=data["company_name"],
            exchange=data.get("exchange", ""),
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
        )


class USStockDatabase:
    """Database of US listed stocks with search capabilities."""

    STOCK_LIST_FILE = DATA_DIR / "us_stocks.json"

    # Major US exchanges
    EXCHANGES = ["NYSE", "NASDAQ", "AMEX"]

    def __init__(self):
        self.stocks: Dict[str, Stock] = {}
        self._name_to_ticker: Dict[str, str] = {}
        self._name_patterns: List[Tuple[re.Pattern, str]] = []
        self._load_or_initialize()

    def _load_or_initialize(self):
        """Load stocks from file or initialize with default data."""
        if self.STOCK_LIST_FILE.exists():
            self._load_from_file()
        else:
            self._initialize_default_stocks()
            self._save_to_file()

    def _load_from_file(self):
        """Load stocks from JSON file."""
        with open(self.STOCK_LIST_FILE, "r") as f:
            data = json.load(f)
            for stock_data in data:
                stock = Stock.from_dict(stock_data)
                self._add_stock(stock)

    def _save_to_file(self):
        """Save stocks to JSON file."""
        data = [stock.to_dict() for stock in self.stocks.values()]
        with open(self.STOCK_LIST_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _add_stock(self, stock: Stock):
        """Add a stock to the database and build search indices."""
        self.stocks[stock.ticker] = stock

        # Build name-to-ticker mapping
        name_lower = stock.company_name.lower()
        self._name_to_ticker[name_lower] = stock.ticker

        # Create regex pattern for company name matching
        # Handle common suffixes and variations
        base_name = self._normalize_company_name(stock.company_name)
        if base_name and len(base_name) >= 3:
            pattern = re.compile(
                r'\b' + re.escape(base_name) + r'(?:\s+(?:inc\.?|corp\.?|co\.?|ltd\.?|llc|plc|corporation|company|incorporated))?\b',
                re.IGNORECASE
            )
            self._name_patterns.append((pattern, stock.ticker))

    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name by removing common suffixes."""
        suffixes = [
            r'\s+inc\.?$', r'\s+corp\.?$', r'\s+co\.?$', r'\s+ltd\.?$',
            r'\s+llc$', r'\s+plc$', r'\s+corporation$', r'\s+company$',
            r'\s+incorporated$', r'\s+holdings?$', r'\s+group$',
            r'\s+technologies$', r'\s+technology$', r'\s+enterprises?$',
            r',\s+inc\.?$', r',\s+corp\.?$',
        ]
        result = name.lower().strip()
        for suffix in suffixes:
            result = re.sub(suffix, '', result, flags=re.IGNORECASE)
        return result.strip()

    def _initialize_default_stocks(self):
        """Initialize with a comprehensive list of major US stocks."""
        # Major US companies across various sectors
        default_stocks = [
            # Technology
            Stock("AAPL", "Apple Inc.", "NASDAQ", "Technology", "Consumer Electronics"),
            Stock("MSFT", "Microsoft Corporation", "NASDAQ", "Technology", "Software"),
            Stock("GOOGL", "Alphabet Inc.", "NASDAQ", "Technology", "Internet"),
            Stock("GOOG", "Alphabet Inc. Class C", "NASDAQ", "Technology", "Internet"),
            Stock("AMZN", "Amazon.com Inc.", "NASDAQ", "Technology", "E-Commerce"),
            Stock("META", "Meta Platforms Inc.", "NASDAQ", "Technology", "Social Media"),
            Stock("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", "Semiconductors"),
            Stock("TSLA", "Tesla Inc.", "NASDAQ", "Technology", "Electric Vehicles"),
            Stock("AMD", "Advanced Micro Devices Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("INTC", "Intel Corporation", "NASDAQ", "Technology", "Semiconductors"),
            Stock("CRM", "Salesforce Inc.", "NYSE", "Technology", "Software"),
            Stock("ORCL", "Oracle Corporation", "NYSE", "Technology", "Software"),
            Stock("ADBE", "Adobe Inc.", "NASDAQ", "Technology", "Software"),
            Stock("CSCO", "Cisco Systems Inc.", "NASDAQ", "Technology", "Networking"),
            Stock("IBM", "International Business Machines", "NYSE", "Technology", "IT Services"),
            Stock("AVGO", "Broadcom Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("QCOM", "Qualcomm Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("TXN", "Texas Instruments Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("NOW", "ServiceNow Inc.", "NYSE", "Technology", "Software"),
            Stock("UBER", "Uber Technologies Inc.", "NYSE", "Technology", "Ride-Sharing"),
            Stock("LYFT", "Lyft Inc.", "NASDAQ", "Technology", "Ride-Sharing"),
            Stock("SNAP", "Snap Inc.", "NYSE", "Technology", "Social Media"),
            Stock("PINS", "Pinterest Inc.", "NYSE", "Technology", "Social Media"),
            Stock("SQ", "Block Inc.", "NYSE", "Technology", "Fintech"),
            Stock("PYPL", "PayPal Holdings Inc.", "NASDAQ", "Technology", "Fintech"),
            Stock("SHOP", "Shopify Inc.", "NYSE", "Technology", "E-Commerce"),
            Stock("SPOT", "Spotify Technology", "NYSE", "Technology", "Streaming"),
            Stock("NFLX", "Netflix Inc.", "NASDAQ", "Technology", "Streaming"),
            Stock("ROKU", "Roku Inc.", "NASDAQ", "Technology", "Streaming"),
            Stock("ZM", "Zoom Video Communications", "NASDAQ", "Technology", "Software"),
            Stock("PLTR", "Palantir Technologies", "NYSE", "Technology", "Software"),
            Stock("SNOW", "Snowflake Inc.", "NYSE", "Technology", "Cloud Computing"),
            Stock("DDOG", "Datadog Inc.", "NASDAQ", "Technology", "Software"),
            Stock("NET", "Cloudflare Inc.", "NYSE", "Technology", "Cloud Computing"),
            Stock("CRWD", "CrowdStrike Holdings", "NASDAQ", "Technology", "Cybersecurity"),
            Stock("ZS", "Zscaler Inc.", "NASDAQ", "Technology", "Cybersecurity"),
            Stock("PANW", "Palo Alto Networks", "NASDAQ", "Technology", "Cybersecurity"),
            Stock("MU", "Micron Technology Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("MRVL", "Marvell Technology", "NASDAQ", "Technology", "Semiconductors"),
            Stock("AMAT", "Applied Materials Inc.", "NASDAQ", "Technology", "Semiconductors"),
            Stock("LRCX", "Lam Research Corporation", "NASDAQ", "Technology", "Semiconductors"),
            Stock("KLAC", "KLA Corporation", "NASDAQ", "Technology", "Semiconductors"),
            Stock("DELL", "Dell Technologies", "NYSE", "Technology", "Hardware"),
            Stock("HPQ", "HP Inc.", "NYSE", "Technology", "Hardware"),
            Stock("HPE", "Hewlett Packard Enterprise", "NYSE", "Technology", "Hardware"),

            # Finance
            Stock("JPM", "JPMorgan Chase & Co.", "NYSE", "Finance", "Banking"),
            Stock("BAC", "Bank of America Corporation", "NYSE", "Finance", "Banking"),
            Stock("WFC", "Wells Fargo & Company", "NYSE", "Finance", "Banking"),
            Stock("C", "Citigroup Inc.", "NYSE", "Finance", "Banking"),
            Stock("GS", "Goldman Sachs Group Inc.", "NYSE", "Finance", "Investment Banking"),
            Stock("MS", "Morgan Stanley", "NYSE", "Finance", "Investment Banking"),
            Stock("BLK", "BlackRock Inc.", "NYSE", "Finance", "Asset Management"),
            Stock("SCHW", "Charles Schwab Corporation", "NYSE", "Finance", "Brokerage"),
            Stock("AXP", "American Express Company", "NYSE", "Finance", "Credit Cards"),
            Stock("V", "Visa Inc.", "NYSE", "Finance", "Payments"),
            Stock("MA", "Mastercard Incorporated", "NYSE", "Finance", "Payments"),
            Stock("COF", "Capital One Financial", "NYSE", "Finance", "Banking"),
            Stock("USB", "U.S. Bancorp", "NYSE", "Finance", "Banking"),
            Stock("PNC", "PNC Financial Services", "NYSE", "Finance", "Banking"),
            Stock("TFC", "Truist Financial Corporation", "NYSE", "Finance", "Banking"),
            Stock("BK", "Bank of New York Mellon", "NYSE", "Finance", "Banking"),
            Stock("STT", "State Street Corporation", "NYSE", "Finance", "Asset Management"),
            Stock("SPGI", "S&P Global Inc.", "NYSE", "Finance", "Financial Data"),
            Stock("MCO", "Moody's Corporation", "NYSE", "Finance", "Credit Ratings"),
            Stock("CME", "CME Group Inc.", "NASDAQ", "Finance", "Exchanges"),
            Stock("ICE", "Intercontinental Exchange", "NYSE", "Finance", "Exchanges"),
            Stock("COIN", "Coinbase Global Inc.", "NASDAQ", "Finance", "Cryptocurrency"),

            # Healthcare
            Stock("JNJ", "Johnson & Johnson", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("UNH", "UnitedHealth Group Inc.", "NYSE", "Healthcare", "Insurance"),
            Stock("PFE", "Pfizer Inc.", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("ABBV", "AbbVie Inc.", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("MRK", "Merck & Co. Inc.", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("LLY", "Eli Lilly and Company", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("TMO", "Thermo Fisher Scientific", "NYSE", "Healthcare", "Life Sciences"),
            Stock("ABT", "Abbott Laboratories", "NYSE", "Healthcare", "Medical Devices"),
            Stock("DHR", "Danaher Corporation", "NYSE", "Healthcare", "Life Sciences"),
            Stock("BMY", "Bristol-Myers Squibb", "NYSE", "Healthcare", "Pharmaceuticals"),
            Stock("AMGN", "Amgen Inc.", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("GILD", "Gilead Sciences Inc.", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("MRNA", "Moderna Inc.", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("REGN", "Regeneron Pharmaceuticals", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("VRTX", "Vertex Pharmaceuticals", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("BIIB", "Biogen Inc.", "NASDAQ", "Healthcare", "Biotechnology"),
            Stock("CVS", "CVS Health Corporation", "NYSE", "Healthcare", "Pharmacy"),
            Stock("WBA", "Walgreens Boots Alliance", "NASDAQ", "Healthcare", "Pharmacy"),
            Stock("CI", "Cigna Group", "NYSE", "Healthcare", "Insurance"),
            Stock("ELV", "Elevance Health Inc.", "NYSE", "Healthcare", "Insurance"),
            Stock("HUM", "Humana Inc.", "NYSE", "Healthcare", "Insurance"),
            Stock("MCK", "McKesson Corporation", "NYSE", "Healthcare", "Distribution"),
            Stock("CAH", "Cardinal Health Inc.", "NYSE", "Healthcare", "Distribution"),
            Stock("ISRG", "Intuitive Surgical Inc.", "NASDAQ", "Healthcare", "Medical Devices"),
            Stock("SYK", "Stryker Corporation", "NYSE", "Healthcare", "Medical Devices"),
            Stock("MDT", "Medtronic plc", "NYSE", "Healthcare", "Medical Devices"),
            Stock("BSX", "Boston Scientific Corp", "NYSE", "Healthcare", "Medical Devices"),
            Stock("ZBH", "Zimmer Biomet Holdings", "NYSE", "Healthcare", "Medical Devices"),

            # Consumer
            Stock("WMT", "Walmart Inc.", "NYSE", "Consumer", "Retail"),
            Stock("COST", "Costco Wholesale Corporation", "NASDAQ", "Consumer", "Retail"),
            Stock("TGT", "Target Corporation", "NYSE", "Consumer", "Retail"),
            Stock("HD", "The Home Depot Inc.", "NYSE", "Consumer", "Retail"),
            Stock("LOW", "Lowe's Companies Inc.", "NYSE", "Consumer", "Retail"),
            Stock("MCD", "McDonald's Corporation", "NYSE", "Consumer", "Restaurants"),
            Stock("SBUX", "Starbucks Corporation", "NASDAQ", "Consumer", "Restaurants"),
            Stock("NKE", "Nike Inc.", "NYSE", "Consumer", "Apparel"),
            Stock("KO", "The Coca-Cola Company", "NYSE", "Consumer", "Beverages"),
            Stock("PEP", "PepsiCo Inc.", "NASDAQ", "Consumer", "Beverages"),
            Stock("PG", "Procter & Gamble Company", "NYSE", "Consumer", "Consumer Goods"),
            Stock("CL", "Colgate-Palmolive Company", "NYSE", "Consumer", "Consumer Goods"),
            Stock("KMB", "Kimberly-Clark Corporation", "NYSE", "Consumer", "Consumer Goods"),
            Stock("EL", "Estee Lauder Companies", "NYSE", "Consumer", "Cosmetics"),
            Stock("LULU", "Lululemon Athletica", "NASDAQ", "Consumer", "Apparel"),
            Stock("DIS", "The Walt Disney Company", "NYSE", "Consumer", "Entertainment"),
            Stock("CMCSA", "Comcast Corporation", "NASDAQ", "Consumer", "Media"),
            Stock("NWSA", "News Corporation", "NASDAQ", "Consumer", "Media"),
            Stock("WBD", "Warner Bros. Discovery", "NASDAQ", "Consumer", "Entertainment"),
            Stock("PARA", "Paramount Global", "NASDAQ", "Consumer", "Entertainment"),
            Stock("EA", "Electronic Arts Inc.", "NASDAQ", "Consumer", "Gaming"),
            Stock("TTWO", "Take-Two Interactive", "NASDAQ", "Consumer", "Gaming"),
            Stock("ATVI", "Activision Blizzard", "NASDAQ", "Consumer", "Gaming"),
            Stock("MAR", "Marriott International", "NASDAQ", "Consumer", "Hotels"),
            Stock("HLT", "Hilton Worldwide Holdings", "NYSE", "Consumer", "Hotels"),
            Stock("ABNB", "Airbnb Inc.", "NASDAQ", "Consumer", "Travel"),
            Stock("BKNG", "Booking Holdings Inc.", "NASDAQ", "Consumer", "Travel"),
            Stock("EXPE", "Expedia Group Inc.", "NASDAQ", "Consumer", "Travel"),
            Stock("LVS", "Las Vegas Sands Corp.", "NYSE", "Consumer", "Casinos"),
            Stock("MGM", "MGM Resorts International", "NYSE", "Consumer", "Casinos"),
            Stock("WYNN", "Wynn Resorts Limited", "NASDAQ", "Consumer", "Casinos"),
            Stock("CMG", "Chipotle Mexican Grill", "NYSE", "Consumer", "Restaurants"),
            Stock("DPZ", "Domino's Pizza Inc.", "NYSE", "Consumer", "Restaurants"),
            Stock("YUM", "Yum! Brands Inc.", "NYSE", "Consumer", "Restaurants"),
            Stock("QSR", "Restaurant Brands International", "NYSE", "Consumer", "Restaurants"),

            # Energy
            Stock("XOM", "Exxon Mobil Corporation", "NYSE", "Energy", "Oil & Gas"),
            Stock("CVX", "Chevron Corporation", "NYSE", "Energy", "Oil & Gas"),
            Stock("COP", "ConocoPhillips", "NYSE", "Energy", "Oil & Gas"),
            Stock("SLB", "Schlumberger Limited", "NYSE", "Energy", "Oil Services"),
            Stock("EOG", "EOG Resources Inc.", "NYSE", "Energy", "Oil & Gas"),
            Stock("PXD", "Pioneer Natural Resources", "NYSE", "Energy", "Oil & Gas"),
            Stock("MPC", "Marathon Petroleum Corp", "NYSE", "Energy", "Refining"),
            Stock("VLO", "Valero Energy Corporation", "NYSE", "Energy", "Refining"),
            Stock("PSX", "Phillips 66", "NYSE", "Energy", "Refining"),
            Stock("OXY", "Occidental Petroleum", "NYSE", "Energy", "Oil & Gas"),
            Stock("HAL", "Halliburton Company", "NYSE", "Energy", "Oil Services"),
            Stock("BKR", "Baker Hughes Company", "NASDAQ", "Energy", "Oil Services"),
            Stock("KMI", "Kinder Morgan Inc.", "NYSE", "Energy", "Pipelines"),
            Stock("WMB", "Williams Companies Inc.", "NYSE", "Energy", "Pipelines"),
            Stock("ENB", "Enbridge Inc.", "NYSE", "Energy", "Pipelines"),

            # Industrials
            Stock("BA", "The Boeing Company", "NYSE", "Industrials", "Aerospace"),
            Stock("CAT", "Caterpillar Inc.", "NYSE", "Industrials", "Machinery"),
            Stock("DE", "Deere & Company", "NYSE", "Industrials", "Machinery"),
            Stock("HON", "Honeywell International", "NASDAQ", "Industrials", "Conglomerate"),
            Stock("GE", "General Electric Company", "NYSE", "Industrials", "Conglomerate"),
            Stock("MMM", "3M Company", "NYSE", "Industrials", "Conglomerate"),
            Stock("LMT", "Lockheed Martin Corporation", "NYSE", "Industrials", "Defense"),
            Stock("RTX", "RTX Corporation", "NYSE", "Industrials", "Defense"),
            Stock("NOC", "Northrop Grumman Corp", "NYSE", "Industrials", "Defense"),
            Stock("GD", "General Dynamics Corp", "NYSE", "Industrials", "Defense"),
            Stock("UPS", "United Parcel Service", "NYSE", "Industrials", "Logistics"),
            Stock("FDX", "FedEx Corporation", "NYSE", "Industrials", "Logistics"),
            Stock("UNP", "Union Pacific Corporation", "NYSE", "Industrials", "Railroads"),
            Stock("CSX", "CSX Corporation", "NASDAQ", "Industrials", "Railroads"),
            Stock("NSC", "Norfolk Southern Corp", "NYSE", "Industrials", "Railroads"),
            Stock("DAL", "Delta Air Lines Inc.", "NYSE", "Industrials", "Airlines"),
            Stock("UAL", "United Airlines Holdings", "NASDAQ", "Industrials", "Airlines"),
            Stock("AAL", "American Airlines Group", "NASDAQ", "Industrials", "Airlines"),
            Stock("LUV", "Southwest Airlines Co.", "NYSE", "Industrials", "Airlines"),
            Stock("F", "Ford Motor Company", "NYSE", "Industrials", "Automotive"),
            Stock("GM", "General Motors Company", "NYSE", "Industrials", "Automotive"),
            Stock("RIVN", "Rivian Automotive Inc.", "NASDAQ", "Industrials", "Electric Vehicles"),
            Stock("LCID", "Lucid Group Inc.", "NASDAQ", "Industrials", "Electric Vehicles"),

            # Real Estate
            Stock("AMT", "American Tower Corporation", "NYSE", "Real Estate", "REITs"),
            Stock("PLD", "Prologis Inc.", "NYSE", "Real Estate", "REITs"),
            Stock("CCI", "Crown Castle Inc.", "NYSE", "Real Estate", "REITs"),
            Stock("EQIX", "Equinix Inc.", "NASDAQ", "Real Estate", "REITs"),
            Stock("SPG", "Simon Property Group", "NYSE", "Real Estate", "REITs"),
            Stock("O", "Realty Income Corporation", "NYSE", "Real Estate", "REITs"),
            Stock("WELL", "Welltower Inc.", "NYSE", "Real Estate", "REITs"),
            Stock("AVB", "AvalonBay Communities", "NYSE", "Real Estate", "REITs"),
            Stock("EQR", "Equity Residential", "NYSE", "Real Estate", "REITs"),
            Stock("DLR", "Digital Realty Trust", "NYSE", "Real Estate", "REITs"),

            # Utilities
            Stock("NEE", "NextEra Energy Inc.", "NYSE", "Utilities", "Electric"),
            Stock("DUK", "Duke Energy Corporation", "NYSE", "Utilities", "Electric"),
            Stock("SO", "Southern Company", "NYSE", "Utilities", "Electric"),
            Stock("D", "Dominion Energy Inc.", "NYSE", "Utilities", "Electric"),
            Stock("AEP", "American Electric Power", "NASDAQ", "Utilities", "Electric"),
            Stock("EXC", "Exelon Corporation", "NASDAQ", "Utilities", "Electric"),
            Stock("SRE", "Sempra Energy", "NYSE", "Utilities", "Electric"),
            Stock("XEL", "Xcel Energy Inc.", "NASDAQ", "Utilities", "Electric"),

            # Telecom
            Stock("T", "AT&T Inc.", "NYSE", "Telecom", "Telecom Services"),
            Stock("VZ", "Verizon Communications", "NYSE", "Telecom", "Telecom Services"),
            Stock("TMUS", "T-Mobile US Inc.", "NASDAQ", "Telecom", "Telecom Services"),

            # Materials
            Stock("LIN", "Linde plc", "NYSE", "Materials", "Chemicals"),
            Stock("APD", "Air Products and Chemicals", "NYSE", "Materials", "Chemicals"),
            Stock("SHW", "Sherwin-Williams Company", "NYSE", "Materials", "Chemicals"),
            Stock("ECL", "Ecolab Inc.", "NYSE", "Materials", "Chemicals"),
            Stock("DD", "DuPont de Nemours Inc.", "NYSE", "Materials", "Chemicals"),
            Stock("DOW", "Dow Inc.", "NYSE", "Materials", "Chemicals"),
            Stock("FCX", "Freeport-McMoRan Inc.", "NYSE", "Materials", "Mining"),
            Stock("NEM", "Newmont Corporation", "NYSE", "Materials", "Mining"),
            Stock("NUE", "Nucor Corporation", "NYSE", "Materials", "Steel"),

            # AI and Emerging Tech
            Stock("AI", "C3.ai Inc.", "NYSE", "Technology", "Artificial Intelligence"),
            Stock("PATH", "UiPath Inc.", "NYSE", "Technology", "Automation"),
            Stock("S", "SentinelOne Inc.", "NYSE", "Technology", "Cybersecurity"),
            Stock("IONQ", "IonQ Inc.", "NYSE", "Technology", "Quantum Computing"),
            Stock("SMCI", "Super Micro Computer", "NASDAQ", "Technology", "Hardware"),
            Stock("ARM", "Arm Holdings plc", "NASDAQ", "Technology", "Semiconductors"),

            # SPACs and Special Situations
            Stock("DWAC", "Digital World Acquisition", "NASDAQ", "Technology", "SPAC"),
            Stock("SPCE", "Virgin Galactic Holdings", "NYSE", "Industrials", "Space"),
            Stock("RKLB", "Rocket Lab USA Inc.", "NASDAQ", "Industrials", "Space"),
        ]

        for stock in default_stocks:
            self._add_stock(stock)

    def get_stock(self, ticker: str) -> Optional[Stock]:
        """Get stock by ticker symbol."""
        return self.stocks.get(ticker.upper())

    def search_by_name(self, name: str) -> Optional[Stock]:
        """Search for a stock by company name."""
        name_lower = name.lower()
        if name_lower in self._name_to_ticker:
            return self.stocks[self._name_to_ticker[name_lower]]
        return None

    def find_mentions(self, text: str) -> List[Tuple[Stock, str]]:
        """
        Find all stock mentions in a given text.

        Returns a list of tuples (Stock, matched_text).
        """
        if not text:
            return []

        mentions = []
        seen_tickers = set()

        # First, search for ticker mentions (as whole words)
        words = set(re.findall(r'\b[A-Z]{1,5}\b', text.upper()))
        for word in words:
            if (word in self.stocks and
                word not in EXCLUDE_COMMON_WORDS and
                len(word) >= MIN_TICKER_LENGTH):
                if word not in seen_tickers:
                    mentions.append((self.stocks[word], word))
                    seen_tickers.add(word)

        # Then, search for company name mentions
        for pattern, ticker in self._name_patterns:
            if ticker not in seen_tickers:
                match = pattern.search(text)
                if match:
                    mentions.append((self.stocks[ticker], match.group()))
                    seen_tickers.add(ticker)

        return mentions

    def get_all_tickers(self) -> Set[str]:
        """Get all ticker symbols in the database."""
        return set(self.stocks.keys())

    def get_all_stocks(self) -> List[Stock]:
        """Get all stocks in the database."""
        return list(self.stocks.values())

    def add_stocks_from_list(self, stocks: List[Stock]):
        """Add multiple stocks to the database."""
        for stock in stocks:
            self._add_stock(stock)
        self._save_to_file()

    def update_from_nasdaq(self) -> int:
        """
        Fetch and update stock list from NASDAQ.
        Returns the number of new stocks added.
        """
        urls = [
            "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000&exchange=NASDAQ",
            "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000&exchange=NYSE",
            "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000&exchange=AMEX",
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        new_count = 0
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    rows = data.get("data", {}).get("rows", [])
                    for row in rows:
                        ticker = row.get("symbol", "").strip()
                        name = row.get("name", "").strip()
                        if ticker and name and ticker not in self.stocks:
                            exchange = "NASDAQ" if "nasdaq" in url.lower() else (
                                "NYSE" if "nyse" in url.lower() else "AMEX"
                            )
                            stock = Stock(
                                ticker=ticker,
                                company_name=name,
                                exchange=exchange,
                                sector=row.get("sector", ""),
                                industry=row.get("industry", ""),
                            )
                            self._add_stock(stock)
                            new_count += 1
            except Exception as e:
                print(f"Error fetching from {url}: {e}")
                continue

        if new_count > 0:
            self._save_to_file()

        return new_count

    def __len__(self) -> int:
        return len(self.stocks)

    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in self.stocks


# Singleton instance
_db_instance: Optional[USStockDatabase] = None


def get_stock_database() -> USStockDatabase:
    """Get the singleton stock database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = USStockDatabase()
    return _db_instance
