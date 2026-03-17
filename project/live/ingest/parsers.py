from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import pandas as pd

@dataclass
class KlineEvent:
    symbol: str
    timeframe: str
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    taker_base_volume: float
    is_final: bool

@dataclass
class BookTickerEvent:
    symbol: str
    timestamp: pd.Timestamp
    best_bid_price: float
    best_bid_qty: float
    best_ask_price: float
    best_ask_qty: float

def parse_kline_event(payload: Dict[str, Any]) -> Optional[KlineEvent]:
    """Parse Binance kline stream message."""
    # Handle combined stream payload
    data = payload.get("data", payload)
    
    event_type = data.get("e")
    if event_type != "kline":
        return None
        
    kline = data.get("k", {})
    
    return KlineEvent(
        symbol=data.get("s", ""),
        timeframe=kline.get("i", ""),
        timestamp=pd.to_datetime(kline.get("t", 0), unit="ms", utc=True),
        open=float(kline.get("o", 0.0)),
        high=float(kline.get("h", 0.0)),
        low=float(kline.get("l", 0.0)),
        close=float(kline.get("c", 0.0)),
        volume=float(kline.get("v", 0.0)),
        quote_volume=float(kline.get("q", 0.0)),
        taker_base_volume=float(kline.get("V", 0.0)),
        is_final=bool(kline.get("x", False)),
    )

def parse_book_ticker_event(payload: Dict[str, Any]) -> Optional[BookTickerEvent]:
    """Parse Binance bookTicker stream message."""
    data = payload.get("data", payload)
    
    event_type = data.get("e")
    if event_type != "bookTicker":
        # Note: best book ticker may not have 'e' field in single stream, 
        # but in combined stream it does if 'stream' name is used.
        # Single stream: {"u":400900217,"s":"BNBUSDT","b":"25.3519","B":"31.21","a":"25.3652","A":"40.66"}
        if "s" in data and "b" in data and "a" in data:
            pass # Valid book ticker
        else:
            return None
            
    return BookTickerEvent(
        symbol=data.get("s", ""),
        timestamp=pd.to_datetime(data.get("E", data.get("T", pd.Timestamp.now().value // 10**6)), unit="ms", utc=True),
        best_bid_price=float(data.get("b", 0.0)),
        best_bid_qty=float(data.get("B", 0.0)),
        best_ask_price=float(data.get("a", 0.0)),
        best_ask_qty=float(data.get("A", 0.0)),
    )
