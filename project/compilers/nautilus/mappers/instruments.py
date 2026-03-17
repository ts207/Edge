from __future__ import annotations

from typing import Dict

def map_to_nautilus_instrument_id(venue: str, instrument: str) -> str:
    """
    Translates internal venue/symbol to Nautilus InstrumentId.
    Example: BINANCE, BTCUSDT-PERP -> BTCUSDT.BINANCE
    """
    # Simple normalization logic
    symbol = instrument.replace("-PERP", "").replace("_", "")
    return f"{symbol}.{venue.upper()}"

def get_nautilus_symbol(internal_symbol: str) -> str:
    """
    Returns the symbol part suitable for Nautilus.
    """
    return internal_symbol.replace("-PERP", "").replace("_", "")
