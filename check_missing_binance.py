import asyncio
import aiohttp
from datetime import datetime, timezone
import logging

ARCHIVE_BASE = "https://data.binance.vision/data/futures/um"

def _next_month(ts):
    year = ts.year + (ts.month // 12)
    month = 1 if ts.month == 12 else ts.month + 1
    return ts.replace(year=year, month=month, day=1)

def _iter_months(start, end):
    months = []
    cursor = start.replace(day=1)
    while cursor <= end:
        months.append(cursor)
        cursor = _next_month(cursor)
    return months

async def check_archive(session, url):
    async with session.head(url) as resp:
        return url, resp.status

async def main():
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = "1m"
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 12, 31, tzinfo=timezone.utc)
    months = _iter_months(start, end)
    
    async with aiohttp.ClientSession() as session:
        for symbol in symbols:
            print(f"\nChecking {symbol} OHLCV 1m...")
            urls = [f"{ARCHIVE_BASE}/monthly/klines/{symbol}/{timeframe}/{symbol}-{timeframe}-{m.year}-{m.month:02d}.zip" for m in months]
            tasks = [check_archive(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            missing = [url for url, status in results if status == 404]
            if missing:
                print(f"  Missing {len(missing)} OHLCV archives for {symbol}:")
                for m in missing:
                    print(f"    - {m}")
            else:
                print(f"  All OHLCV archives present for {symbol}.")

            print(f"\nChecking {symbol} Mark Price 1m...")
            urls = [f"{ARCHIVE_BASE}/monthly/markPriceKlines/{symbol}/1m/{symbol}-1m-{m.year}-{m.month:02d}.zip" for m in months]
            tasks = [check_archive(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            missing = [url for url, status in results if status == 404]
            if missing:
                print(f"  Missing {len(missing)} Mark Price archives for {symbol}:")
                for m in missing:
                    print(f"    - {m}")
            else:
                print(f"  All Mark Price archives present for {symbol}.")

if __name__ == "__main__":
    asyncio.run(main())
