from __future__ import annotations

from typing import Dict, Any

def map_execution_intent(style: str, post_only: bool) -> Dict[str, Any]:
    """
    Maps abstract execution style to Nautilus execution commands and order types.
    """
    mapping = {
        "market": {
            "order_type": "MARKET",
            "time_in_force": None,
            "exec_path": "direct"
        },
        "passive": {
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "post_only": True,
            "exec_path": "passive_liquidity"
        },
        "passive_then_cross": {
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "post_only": False,
            "exec_path": "aggressive_cross",
            "retry_limit": 3
        },
        "limit": {
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "post_only": post_only,
            "exec_path": "direct"
        }
    }
    
    return mapping.get(style.lower(), mapping["market"])
