import pandas as pd
from typing import Dict, List

def order_blocks(df: pd.DataFrame, trend: str, lookback: int = 50) -> List[Dict]:
    """
    Find order blocks - strong impulse candles that get broken/mitigated
    - Bullish OB: bullish candle followed by pullback
    - Bearish OB: bearish candle followed by reversal up
    
    Returns list with 'high', 'low', 'close', 'open', and 'ob_id'
    """
    blocks = []
    recent = df.iloc[-lookback:].copy()
    ob_counter = 0
    
    if trend == "bullish":
        # Looking for bullish candles (strong closes up)
        for i in range(1, len(recent) - 2):
            current = recent.iloc[i]
            next_candle = recent.iloc[i + 1]
            
            # Strong bullish candle
            is_strong = (current['close'] > current['open']) and \
                       ((current['close'] - current['open']) > (current['high'] - current['low']) * 0.6)
            
            # Followed by lower low (pullback)
            has_pullback = next_candle['low'] < current['low']
            
            if is_strong and has_pullback:
                ob_counter += 1
                blocks.append({
                    'high': current['high'],
                    'low': current['low'],
                    'close': current['close'],
                    'open': current['open'],
                    'ob_id': f"OB_{ob_counter}",
                })
    
    elif trend == "bearish":
        # Looking for bearish candles (strong closes down)
        for i in range(1, len(recent) - 2):
            current = recent.iloc[i]
            next_candle = recent.iloc[i + 1]
            
            # Strong bearish candle
            is_strong = (current['close'] < current['open']) and \
                       ((current['open'] - current['close']) > (current['high'] - current['low']) * 0.6)
            
            # Followed by higher high (pullback)
            has_pullback = next_candle['high'] > current['high']
            
            if is_strong and has_pullback:
                ob_counter += 1
                blocks.append({
                    'high': current['high'],
                    'low': current['low'],
                    'close': current['close'],
                    'open': current['open'],
                    'ob_id': f"OB_{ob_counter}",
                })
    
    return blocks