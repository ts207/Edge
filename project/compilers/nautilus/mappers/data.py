from __future__ import annotations

from typing import Dict, Any, List

def map_data_requirements(
    bars: List[str], 
    book: bool, 
    depth_fidelity: str
) -> Dict[str, Any]:
    """
    Maps research data requirements to Nautilus data loading and subscription config.
    """
    nautilus_bars = []
    for b in bars:
        # Nautilus often uses BarType(instrument_id, interval, price_type)
        nautilus_bars.append({
            "spec": b,
            "price_type": "MID"
        })
        
    return {
        "bar_subscriptions": nautilus_bars,
        "book_subscription": book,
        "book_depth": 5 if depth_fidelity == "top_5" else (1 if depth_fidelity == "tob" else 20),
        "quote_subscription": True # Always subscribe to quotes for execution realism
    }
