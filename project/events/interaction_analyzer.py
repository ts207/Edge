import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

class InteractionOp:
    AND = "and"
    OR = "or"
    CONFIRM = "confirm"
    EXCLUDE = "exclude"

def detect_interactions(
    df: pd.DataFrame, 
    left_id: str, 
    right_id: str, 
    op: str, 
    lag: int,
    interaction_name: str
) -> pd.DataFrame:
    """
    Detect intersections between two mechanisms (events/states).
    """
    results = []
    
    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("signal_ts")
        
        left_mask = group['event_type'] == left_id
        right_mask = group['event_type'] == right_id
        
        left_ts = group.loc[left_mask, "signal_ts"].tolist()
        right_ts = group.loc[right_mask, "signal_ts"].tolist()
        
        if op == InteractionOp.AND:
            for l_ts in left_ts:
                if any(abs(r_ts - l_ts) <= lag for r_ts in right_ts):
                    results.append({
                        "symbol": symbol,
                        "interaction_id": interaction_name,
                        "signal_ts": l_ts,
                    })
        elif op == InteractionOp.CONFIRM:
            zero_td = pd.Timedelta(0) if isinstance(lag, pd.Timedelta) else 0
            for l_ts in left_ts:
                matching_rights = [r_ts for r_ts in right_ts if zero_td < (r_ts - l_ts) <= lag]
                if matching_rights:
                    trigger_ts = matching_rights[0]
                    results.append({
                        "symbol": symbol,
                        "interaction_id": interaction_name,
                        "signal_ts": trigger_ts,
                    })
        elif op == InteractionOp.EXCLUDE:
            for l_ts in left_ts:
                if not any(abs(r_ts - l_ts) <= lag for r_ts in right_ts):
                    results.append({
                        "symbol": symbol,
                        "interaction_id": interaction_name,
                        "signal_ts": l_ts,
                    })
                    
    return pd.DataFrame(results)
