import pandas as pd
from project.strategy.templates.spec import StrategySpec
from project.strategy.templates.data_bundle import DataBundle

def compile_positions(spec: StrategySpec, bundle: DataBundle) -> tuple[pd.Series, pd.DataFrame]:
    """Compile a spec into an integer position series avoiding lookahead."""
    idx = bundle.prices.index
    positions = pd.Series(0.0, index=idx)
    debug = pd.DataFrame(index=idx)
    
    entries = bundle.get_event_signal(spec.event_family, spec.entry_signal)
    exits = bundle.get_event_signal(spec.event_family, spec.exit_signal)
    
    in_position = False
    cooldown_until = 0
    cap = spec.position_cap
    
    # Vectorized approaches via shift boundaries ensures closed-left invariant
    pos_arr = positions.to_numpy(copy=True)
    ent_arr = entries.to_numpy(copy=True)
    ext_arr = exits.to_numpy(copy=True)
    
    for i in range(len(idx)):
        if ext_arr[i] and in_position:
            pos_arr[i] = 0.0
            in_position = False
            cooldown_until = i + spec.cooldown_bars
        elif ent_arr[i] and not in_position and i >= cooldown_until:
            pos_arr[i] = cap
            in_position = True
        elif i > 0:
            pos_arr[i] = pos_arr[i-1]
            
    positions = pd.Series(pos_arr, index=idx)
    debug = pd.DataFrame({"entries": entries, "exits": exits, "positions": positions})
    return positions, debug
