from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from project.live.ingest.ws_client import BinanceWebSocketClient
from project.live.ingest.parsers import parse_book_ticker_event, parse_kline_event

_LOG = logging.getLogger(__name__)


class LiveDataManager:
    def __init__(
        self,
        symbols: List[str],
        on_reconnect_exhausted: Optional[Callable[[], None]] = None,
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

    def _build_streams(self) -> List[str]:
        streams = []
        for symbol in self.symbols:
            streams.append(f"{symbol}@kline_1m")
            streams.append(f"{symbol}@kline_5m")
            streams.append(f"{symbol}@bookTicker")
        return streams

    async def start(self):
        _LOG.info("Starting Live Data Manager...")
        self._loop = asyncio.get_running_loop()
        await self.client.connect()

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

        if "kline" in stream_name:
            event = parse_kline_event(message)
            if event:
                self._enqueue_threadsafe(self.kline_queue, event, "Kline")
        elif "bookTicker" in stream_name or "b" in message.get("data", message):
            event = parse_book_ticker_event(message)
            if event:
                self._enqueue_threadsafe(self.ticker_queue, event, "Ticker")
