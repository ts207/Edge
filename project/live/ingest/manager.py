from __future__ import annotations

import asyncio
import logging
from datetime import timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from project.live.ingest.ws_client import BinanceWebSocketClient
from project.live.ingest.parsers import parse_book_ticker_event, parse_kline_event

_LOG = logging.getLogger(__name__)


class LiveDataManager:
    def __init__(
        self,
        symbols: List[str],
        on_reconnect_exhausted: Optional[Callable[[], None]] = None,
        rest_client: Any | None = None,
    ):
        self.symbols = [s.lower() for s in symbols]
        self.kline_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.ticker_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._loop: asyncio.AbstractEventLoop | None = None
        self.streams = self._build_streams()
        self.client = BinanceWebSocketClient(
            self.streams,
            self._on_message,
            on_reconnect_exhausted=on_reconnect_exhausted,
        )
        self.rest_client = rest_client

    def _build_streams(self) -> List[str]:
        streams = []
        for symbol in self.symbols:
            streams.append(f"{symbol}@kline_1m")
            streams.append(f"{symbol}@kline_5m")
            streams.append(f"{symbol}@bookTicker")
        return streams

    def health_monitor_keys(self) -> List[tuple[str, str]]:
        keys: List[tuple[str, str]] = []
        for stream in self.streams:
            if "@" not in stream:
                continue
            symbol, channel = stream.split("@", 1)
            if channel == "bookTicker":
                keys.append((symbol.upper(), "ticker"))
            elif channel.startswith("kline_"):
                timeframe = channel.split("_", 1)[1]
                keys.append((symbol.upper(), f"kline:{timeframe}"))
        return keys

    async def start(self):
        _LOG.info("Starting Live Data Manager...")
        self._loop = asyncio.get_running_loop()
        
        if self.rest_client:
            await self.backfill()
            
        await self.client.connect()

    async def backfill(self):
        """Perform a conservative REST backfill for all symbols/timeframes."""
        if not self.rest_client:
            return
            
        _LOG.info("Performing initial REST backfill...")
        for symbol in self.symbols:
            try:
                # Backfill 1m klines (100 bars)
                klines = await self.rest_client.get_klines(symbol, "1m", limit=100)
                for k in klines:
                    # Construct a kline event object similar to what parse_kline_event produces
                    event = {
                        "symbol": symbol.upper(),
                        "timeframe": "1m",
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "is_final": True,
                        "timestamp": pd.to_datetime(k[0], unit="ms", utc=True),
                    }
                    self.kline_queue.put_nowait(event)
            except Exception as e:
                _LOG.error(f"Failed to backfill {symbol}: {e}")

    async def stop(self):
        _LOG.info("Stopping Live Data Manager...")
        await self.client.disconnect()

    def _enqueue_threadsafe(self, queue: asyncio.Queue, event: Dict[str, Any], label: str) -> None:
        loop = self._loop
        if loop is None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
            return

        def _push() -> None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                _LOG.warning("%s queue full, dropping oldest event", label)
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

        if loop.is_running():
            loop.call_soon_threadsafe(_push)
        else:
            _push()

    def _on_message(self, message: Dict[str, Any]):
        stream_name = message.get("stream", "")
        arrival_ts = pd.Timestamp.now(timezone.utc)

        if "kline" in stream_name:
            event = parse_kline_event(message)
            if event:
                self._enqueue_threadsafe(self.kline_queue, event, "Kline")
        elif "bookTicker" in stream_name or "b" in message.get("data", message):
            event = parse_book_ticker_event(message, arrival_ts)
            if event:
                self._enqueue_threadsafe(self.ticker_queue, event, "Ticker")
