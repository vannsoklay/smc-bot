import pandas as pd
from typing import Dict, List

def fair_value_gaps(df: pd.DataFrame, trend: str, lookback: int = 50) -> List[Dict]:
    """
    Find Fair Value Gaps (FVG) - unfilled gaps in price
    - Bullish FVG: gap up that hasn't been filled yet
    - Bearish FVG: gap down that hasn't been filled yet
    """
    gaps = []
    recent = df.iloc[-lookback:].copy()
    
    for i in range(1, len(recent) - 1):
        prev_candle = recent.iloc[i - 1]
        current = recent.iloc[i]
        
        if trend == "bullish":
            # Gap up: previous high < current low
            if prev_candle['high'] < current['low']:
                gap_low = prev_candle['high']
                gap_high = current['low']
                
                # Check if gap is still unfilled
                future_lows = recent['low'].iloc[i:].min()
                
                if future_lows > gap_low:  # Gap not filled
                    gaps.append({
                        'high': gap_high,
                        'low': gap_low,
                    })
        
        elif trend == "bearish":
            # Gap down: previous low > current high
            if prev_candle['low'] > current['high']:
                gap_high = prev_candle['low']
                gap_low = current['high']
                
                # Check if gap is still unfilled
                future_highs = recent['high'].iloc[i:].max()
                
                if future_highs < gap_high:  # Gap not filled
                    gaps.append({
                        'high': gap_high,
                        'low': gap_low,
                    })
    
    return gaps