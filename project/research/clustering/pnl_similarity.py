import pandas as pd
import numpy as np
from typing import Dict, List

def calculate_similarity_matrix(pnl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate similarity between hypotheses based on PnL correlation and overlap.
    pnl_df: columns are hypothesis_ids, index is signal_ts
    """
    # 1. Return correlation
    corr_matrix = pnl_df.corr().fillna(0)
    
    # 2. Entry overlap (optional but recommended in plan)
    # We'll stick to return correlation as the primary metric for now
    
    return corr_matrix

def compute_distance_matrix(similarity_matrix: pd.DataFrame) -> pd.DataFrame:
    """Convert similarity to distance: d = 1 - corr"""
    return 1 - similarity_matrix
