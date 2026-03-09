"""
Run TWAP strategy with real data from Binance
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from decimal import Decimal
import sys

# Fetch real data from Binance
def fetch_btc_data():
    print("=" * 60)
    print("Fetching REAL BTC/USDT data from Binance API...")
    print("=" * 60)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "startTime": int(start_time.timestamp() * 1000),
        "endTime": int(end_time.timestamp() * 1000)
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"[OK] Successfully fetched {len(data)} records from Binance")

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])

        # Convert types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        print(f"[OK] Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
        print()

        return df

    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")
        return None


# Simple TWAP strategy simulation
def run_twap_strategy(df):
    print("=" * 60)
    print("Running TWAP Strategy with REAL Data")
    print("=" * 60)
    print()

    # TWAP parameters
    total_quantity = Decimal('1000')  # Target: 1000 BTC
    num_slices = 12
    slice_qty = total_quantity / num_slices

    print("Strategy Parameters:")
    print(f"  Symbol: BTCUSDT")
    print(f"  Side: BUY")
    print(f"  Total Quantity: {total_quantity} BTC")
    print(f"  Duration: 2 minutes (simulated)")
    print(f"  Slices: {num_slices}")
    print(f"  Quantity per slice: {slice_qty:.2f} BTC")
    print()

    # Simulate execution
    results = {
        'slices': [],
        'total_filled': Decimal('0'),
        'total_cost': Decimal('0'),
        'avg_price': Decimal('0')
    }

    print("Execution Log:")
    print("-" * 60)

    for i in range(num_slices):
        # Get price from real data (cycle through the data)
        price_idx = i % len(df)
        price = Decimal(str(df['close'].iloc[price_idx]))

        # Execute slice
        fill_qty = slice_qty
        fill_cost = fill_qty * price

        results['slices'].append({
            'index': i + 1,
            'price': price,
            'quantity': fill_qty,
            'cost': fill_cost
        })

        results['total_filled'] += fill_qty
        results['total_cost'] += fill_cost

        print(f"Slice {i+1:2d}/{num_slices}: Filled {fill_qty:8.2f} BTC @ ${price:10.2f} = ${fill_cost:15.2f}")

        # Simulate time delay (just for show)
        time.sleep(0.1)

    print("-" * 60)
    print()

    # Calculate final statistics
    if results['total_filled'] > 0:
        results['avg_price'] = results['total_cost'] / results['total_filled']

    # Print summary
    print("=" * 60)
    print("TWAP EXECUTION SUMMARY (REAL DATA)")
    print("=" * 60)
    print()
    print(f"  Total Quantity:     {total_quantity:15.2f} BTC")
    print(f"  Total Filled:       {results['total_filled']:15.2f} BTC ({(results['total_filled']/total_quantity*100):.1f}%)")
    print(f"  Total Cost:        ${results['total_cost']:15.2f} USDT")
    print(f"  Average Price:     ${results['avg_price']:15.2f} USDT/BTC")
    print()
    print(f"  Strategy VWAP:     ${results['avg_price']:15.2f}")
    print()
    print("  Note: Prices are from REAL Binance historical data!")
    print()
    print("=" * 60)

    return results


if __name__ == "__main__":
    import time

    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + "  MARKET MAKING BACKTEST FRAMEWORK".center(58) + "║")
    print("║" + "  TWAP Strategy with REAL Data".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Step 1: Fetch real data
    df = fetch_btc_data()

    if df is None or df.empty:
        print("[ERROR] Failed to fetch data. Exiting.")
        sys.exit(1)

    # Step 2: Run TWAP strategy
    results = run_twap_strategy(df)

    print()
    print("[OK] Execution complete!")
    print()
