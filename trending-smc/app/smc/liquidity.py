import pandas as pd
def liquidity_sweep(df: pd.DataFrame, trend: str) -> bool:
    """
    Detect if price swept liquidity
    - Bullish: price touched recent highs (bearish liquidity) and pulled back
    - Bearish: price touched recent lows (bullish liquidity) and pulled back
    """
    if len(df) < 5:
        return False
    
    recent = df.iloc[-5:].copy()
    current = df.iloc[-1]
    previous = df.iloc[-2]
    
    if trend == "bullish":
        # Looking for bearish liquidity sweep (recent highs)
        recent_high = recent['high'].max()
        
        # Sweep if: previous candle touched high, current closed below it
        if previous['high'] >= recent_high * 0.99:
            if current['close'] < recent_high:
                return True
        
        # Or current high touched but closed down
        if current['high'] >= recent_high * 0.99:
            if current['close'] < current['open']:
                return True
    
    elif trend == "bearish":
        # Looking for bullish liquidity sweep (recent lows)
        recent_low = recent['low'].min()
        
        # Sweep if: previous candle touched low, current closed above it
        if previous['low'] <= recent_low * 1.01:
            if current['close'] > recent_low:
                return True
        
        # Or current low touched but closed up
        if current['low'] <= recent_low * 1.01:
            if current['close'] > current['open']:
                return True
    
    return False
