"""
Fetch all finance-related events from Polymarket and export to CSV.
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from polymarket_client import PolymarketClient


def fetch_finance_events(output_file: str = "finance_events.csv", max_markets: int = None):
    """
    Fetch all finance-related events from Polymarket and save to CSV.

    Args:
        output_file: Output CSV file path
        max_markets: Maximum number of markets to fetch (None for all)
    """
    print("Initializing Polymarket client...")
    client = PolymarketClient()

    # Keywords that indicate finance-related events
    finance_keywords = [
        # Stock related
        "stock", "share", "nasdaq", "nyse", "s&p", "dow", "market cap",
        "ipo", "earnings", "dividend", "bull", "bear", "trading",
        # Company/ticker patterns
        "(aapl)", "(tsla)", "(msft)", "(googl)", "(amzn)", "(meta)", "(nvda)",
        "(amd)", "(intc)", "(nflx)", "(dis)", "(ba)", "(gm)", "(f)",
        # Crypto
        "bitcoin", "btc", "ethereum", "eth", "crypto", "coinbase",
        # Economy
        "fed", "interest rate", "inflation", "gdp", "recession", "economy",
        "federal reserve", "treasury", "bond", "yield",
        # Finance general
        "bank", "financial", "investor", "wall street", "hedge fund",
        "sec", "regulation", "merger", "acquisition", "bankruptcy",
        # Specific companies often in prediction markets
        "tesla", "apple", "amazon", "google", "microsoft", "nvidia",
        "meta", "facebook", "twitter", "openai", "spacex",
    ]

    print("Fetching markets from Polymarket...")
    print("This may take a while...")

    finance_markets = []
    total_scanned = 0

    for market in client.get_all_markets(max_markets=max_markets, include_closed=True):
        total_scanned += 1

        # Check if market is finance-related
        question_lower = market.question.lower() if market.question else ""
        description_lower = market.description.lower() if market.description else ""
        combined_text = question_lower + " " + description_lower

        is_finance = any(keyword in combined_text for keyword in finance_keywords)

        if is_finance:
            finance_markets.append({
                "created_at": market.created_at.strftime("%Y-%m-%d %H:%M:%S") if market.created_at else "",
                "question": market.question,
                "url": market.url,
                "closed": market.closed,
                "resolved": market.resolved,
            })

        # Progress update every 100 markets
        if total_scanned % 100 == 0:
            print(f"Scanned {total_scanned} markets, found {len(finance_markets)} finance events...")

    print(f"\nTotal markets scanned: {total_scanned}")
    print(f"Finance events found: {len(finance_markets)}")

    # Sort by created_at date
    finance_markets.sort(key=lambda x: x["created_at"], reverse=True)

    # Write to CSV
    output_path = Path(output_file)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["created_at", "question", "url", "closed", "resolved"])
        writer.writeheader()
        writer.writerows(finance_markets)

    print(f"\nExported to: {output_path.absolute()}")
    return finance_markets


if __name__ == "__main__":
    # You can change max_markets to limit the scan, or set to None for all
    fetch_finance_events(
        output_file="finance_events.csv",
        max_markets=2000  # Set to None to fetch all markets
    )
