#!/usr/bin/env python3
"""
Polymarket First Mention Tracker

Identifies when US listed firms are first mentioned on Polymarket prediction markets.

Usage:
    python main.py scan [--max-markets N] [--include-closed]
    python main.py scan-new
    python main.py lookup TICKER
    python main.py search TICKER
    python main.py list [--limit N] [--sector SECTOR]
    python main.py export [--output FILE]
    python main.py stats
    python main.py update-stocks
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DATA_DIR


def print_progress(scanned: int, total: int, message: str):
    """Print progress during scanning."""
    if total > 0:
        pct = (scanned / total) * 100
        print(f"\r[{scanned}/{total}] ({pct:.1f}%) {message[:60]:<60}", end="", flush=True)
    else:
        print(f"\r[{scanned}] {message[:70]:<70}", end="", flush=True)


def cmd_scan(args):
    """Scan all Polymarket markets for stock mentions."""
    from tracker import create_tracker

    print("Initializing tracker...")
    tracker = create_tracker()

    print(f"Stock database contains {len(tracker.stock_db)} stocks")
    print(f"Starting scan of Polymarket markets...")
    print()

    result = tracker.scan_all_markets(
        max_markets=args.max_markets,
        include_closed=args.include_closed,
        progress_callback=print_progress if not args.quiet else None,
    )

    print()  # New line after progress
    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Markets scanned:      {result.markets_scanned}")
    print(f"Markets skipped:      {result.skipped_markets}")
    print(f"New first mentions:   {result.new_first_mentions}")
    print(f"Total mentions found: {result.total_mentions_found}")
    print(f"Errors:               {result.errors}")
    print()

    if result.new_first_mentions > 0:
        print("New first mentions found:")
        print("-" * 40)
        recent = tracker.get_recent_first_mentions(days=1)
        for mention in recent[-10:]:  # Show last 10
            print(f"  {mention.ticker}: {mention.company_name}")
            print(f"    Date: {mention.first_mention_date.strftime('%Y-%m-%d')}")
            print(f"    Market: {mention.market_question[:60]}...")
            print()


def cmd_scan_new(args):
    """Scan only new markets since last scan."""
    from tracker import create_tracker

    print("Initializing tracker...")
    tracker = create_tracker()

    last_scan = tracker.storage.last_processed_date
    if last_scan:
        print(f"Last scan: {last_scan.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No previous scan found. Performing full scan...")

    print("Scanning new markets...")
    print()

    result = tracker.scan_new_markets(
        progress_callback=print_progress if not args.quiet else None,
    )

    print()
    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Markets scanned:      {result.markets_scanned}")
    print(f"New first mentions:   {result.new_first_mentions}")
    print(f"Errors:               {result.errors}")


def cmd_lookup(args):
    """Look up the first mention for a specific stock."""
    from tracker import create_tracker

    tracker = create_tracker()
    ticker = args.ticker.upper()

    # First check if the stock exists in our database
    stock = tracker.stock_db.get_stock(ticker)
    if not stock:
        print(f"Stock {ticker} not found in database.")
        print("Use 'python main.py update-stocks' to update the stock database.")
        return

    print(f"Stock: {stock.ticker} - {stock.company_name}")
    print(f"Exchange: {stock.exchange}")
    print(f"Sector: {stock.sector}")
    print(f"Industry: {stock.industry}")
    print()

    mention = tracker.get_first_mention(ticker)
    if mention:
        print("First Mention on Polymarket:")
        print("-" * 40)
        print(f"Date:     {mention.first_mention_date.strftime('%Y-%m-%d')}")
        print(f"Market:   {mention.market_question}")
        print(f"URL:      {mention.market_url}")
        print(f"Matched:  '{mention.matched_text}'")
        if mention.market_description:
            print(f"Description: {mention.market_description[:200]}...")
    else:
        print("No mention found on Polymarket.")
        print("Run 'python main.py scan' to scan for mentions.")


def cmd_search(args):
    """Search Polymarket for markets mentioning a stock."""
    from tracker import create_tracker

    tracker = create_tracker()
    ticker = args.ticker.upper()

    stock = tracker.stock_db.get_stock(ticker)
    if not stock:
        print(f"Stock {ticker} not found in database.")
        return

    print(f"Searching for markets mentioning {stock.ticker} ({stock.company_name})...")
    print()

    markets = tracker.search_stock_markets(ticker, limit=args.limit)

    if not markets:
        print("No markets found.")
        return

    print(f"Found {len(markets)} markets:")
    print("=" * 60)

    for i, market in enumerate(markets, 1):
        print(f"\n{i}. {market.question}")
        print(f"   Created: {market.created_at.strftime('%Y-%m-%d') if market.created_at else 'Unknown'}")
        print(f"   Status: {'Closed' if market.closed else 'Open'}")
        print(f"   URL: {market.url}")


def cmd_list(args):
    """List all tracked first mentions."""
    from tracker import create_tracker

    tracker = create_tracker()
    mentions = tracker.get_all_first_mentions()

    if args.sector:
        mentions = [m for m in mentions if m.sector.lower() == args.sector.lower()]

    if not mentions:
        print("No first mentions tracked yet.")
        print("Run 'python main.py scan' to scan for mentions.")
        return

    # Apply limit
    if args.limit and args.limit < len(mentions):
        mentions = mentions[-args.limit:]  # Most recent

    print(f"First Mentions of US Stocks on Polymarket ({len(mentions)} records)")
    print("=" * 80)
    print()
    print(f"{'Ticker':<8} {'Company':<30} {'Date':<12} {'Sector':<15}")
    print("-" * 80)

    for mention in mentions:
        company_short = mention.company_name[:28] + ".." if len(mention.company_name) > 30 else mention.company_name
        sector_short = mention.sector[:13] + ".." if len(mention.sector) > 15 else mention.sector
        print(
            f"{mention.ticker:<8} "
            f"{company_short:<30} "
            f"{mention.first_mention_date.strftime('%Y-%m-%d'):<12} "
            f"{sector_short:<15}"
        )

    print()
    print(f"Total: {len(mentions)} stocks")


def cmd_export(args):
    """Export first mentions to CSV file."""
    from storage import get_storage

    storage = get_storage()
    output_path = Path(args.output) if args.output else DATA_DIR / "first_mentions.csv"

    count = storage.export_to_csv(output_path)

    if count > 0:
        print(f"Exported {count} records to {output_path}")
    else:
        print("No data to export. Run 'python main.py scan' first.")


def cmd_stats(args):
    """Display tracking statistics."""
    from tracker import create_tracker

    tracker = create_tracker()
    stats = tracker.get_statistics()

    print("Polymarket First Mention Tracker Statistics")
    print("=" * 50)
    print()

    storage_stats = stats["storage"]
    print(f"Total first mentions tracked: {storage_stats['total_mentions']}")
    print(f"Total markets processed:      {storage_stats['processed_markets']}")
    print(f"Stock database size:          {stats['stock_database_size']}")
    print()

    if storage_stats.get("date_range"):
        date_range = storage_stats["date_range"]
        print(f"Date range: {date_range['earliest'][:10]} to {date_range['latest'][:10]}")
        print()

    if storage_stats.get("sectors"):
        print("Mentions by Sector:")
        print("-" * 30)
        for sector, count in sorted(
            storage_stats["sectors"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {sector:<20} {count}")
        print()

    if storage_stats.get("exchanges"):
        print("Mentions by Exchange:")
        print("-" * 30)
        for exchange, count in sorted(
            storage_stats["exchanges"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {exchange:<20} {count}")


def cmd_update_stocks(args):
    """Update the stock database from NASDAQ."""
    from us_stocks import get_stock_database

    print("Updating stock database from NASDAQ...")
    db = get_stock_database()

    initial_count = len(db)
    new_count = db.update_from_nasdaq()

    print(f"Initial stocks: {initial_count}")
    print(f"New stocks added: {new_count}")
    print(f"Total stocks: {len(db)}")


def main():
    parser = argparse.ArgumentParser(
        description="Track first mentions of US listed firms on Polymarket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scan                    # Scan all markets
  python main.py scan --max-markets 100  # Scan first 100 markets
  python main.py scan-new                # Scan only new markets
  python main.py lookup AAPL             # Look up Apple's first mention
  python main.py search TSLA             # Search for Tesla markets
  python main.py list --limit 20         # List last 20 first mentions
  python main.py export                  # Export to CSV
  python main.py stats                   # Show statistics
  python main.py update-stocks           # Update stock database
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan all Polymarket markets")
    scan_parser.add_argument(
        "--max-markets", "-m", type=int, default=None,
        help="Maximum number of markets to scan"
    )
    scan_parser.add_argument(
        "--include-closed", "-c", action="store_true", default=True,
        help="Include closed markets (default: True)"
    )
    scan_parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output"
    )
    scan_parser.set_defaults(func=cmd_scan)

    # scan-new command
    scan_new_parser = subparsers.add_parser("scan-new", help="Scan new markets since last scan")
    scan_new_parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output"
    )
    scan_new_parser.set_defaults(func=cmd_scan_new)

    # lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Look up a stock's first mention")
    lookup_parser.add_argument("ticker", help="Stock ticker symbol")
    lookup_parser.set_defaults(func=cmd_lookup)

    # search command
    search_parser = subparsers.add_parser("search", help="Search for markets mentioning a stock")
    search_parser.add_argument("ticker", help="Stock ticker symbol")
    search_parser.add_argument(
        "--limit", "-l", type=int, default=20,
        help="Maximum results to return (default: 20)"
    )
    search_parser.set_defaults(func=cmd_search)

    # list command
    list_parser = subparsers.add_parser("list", help="List all tracked first mentions")
    list_parser.add_argument(
        "--limit", "-l", type=int, default=None,
        help="Limit number of results"
    )
    list_parser.add_argument(
        "--sector", "-s", type=str, default=None,
        help="Filter by sector"
    )
    list_parser.set_defaults(func=cmd_list)

    # export command
    export_parser = subparsers.add_parser("export", help="Export first mentions to CSV")
    export_parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output file path"
    )
    export_parser.set_defaults(func=cmd_export)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Display tracking statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # update-stocks command
    update_stocks_parser = subparsers.add_parser(
        "update-stocks",
        help="Update stock database from NASDAQ"
    )
    update_stocks_parser.set_defaults(func=cmd_update_stocks)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.command == "scan":
            print("Your progress has been saved. Run again to continue.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
