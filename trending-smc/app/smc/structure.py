# app/smc/structure.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def find_swing_highs(df: pd.DataFrame, window: int = 5) -> List[int]:
    """Find indices of swing highs"""
    highs = []
    for i in range(window, len(df) - window):
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            highs.append(i)
    return highs


def find_swing_lows(df: pd.DataFrame, window: int = 5) -> List[int]:
    """Find indices of swing lows"""
    lows = []
    for i in range(window, len(df) - window):
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            lows.append(i)
    return lows


def htf_trend(df: pd.DataFrame, lookback: int = 50) -> str:
    """
    Identify trend direction on HTF
    Improved version with multiple methods
    
    Returns: 'bullish', 'bearish', or 'range'
    """
    if len(df) < 20:
        return "range"
    
    recent = df.iloc[-lookback:].copy()
    
    # ========== METHOD 1: Swing Structure ==========
    highs = find_swing_highs(recent, window=5)
    lows = find_swing_lows(recent, window=5)
    
    # Need at least 2 swings to determine trend
    if len(highs) >= 2 and len(lows) >= 2:
        last_high = recent['high'].iloc[highs[-1]]
        prev_high = recent['high'].iloc[highs[-2]]
        last_low = recent['low'].iloc[lows[-1]]
        prev_low = recent['low'].iloc[lows[-2]]
        
        # Higher High + Higher Low = Bullish
        if last_high > prev_high and last_low > prev_low:
            return "bullish"
        
        # Lower High + Lower Low = Bearish
        if last_high < prev_high and last_low < prev_low:
            return "bearish"
    
    # ========== METHOD 2: Moving Average Crossover ==========
    # If swing detection fails, use MA trend
    sma_20 = recent['close'].rolling(window=20).mean()
    sma_50 = recent['close'].rolling(window=50).mean()
    
    current_close = recent['close'].iloc[-1]
    current_ma20 = sma_20.iloc[-1]
    current_ma50 = sma_50.iloc[-1]
    
    # Price above both MAs = Bullish
    if current_close > current_ma20 > current_ma50:
        return "bullish"
    
    # Price below both MAs = Bearish
    if current_close < current_ma20 < current_ma50:
        return "bearish"
    
    # ========== METHOD 3: Higher Highs & Lows (Simpler) ==========
    # Look at last 10 candles
    last_10 = recent.iloc[-10:].copy()
    
    # Check if price is making progression
    high_progression = last_10['high'].iloc[-1] > last_10['high'].iloc[:-1].max()
    low_progression = last_10['low'].iloc[-1] > last_10['low'].iloc[:-1].min()
    
    if high_progression and low_progression:
        return "bullish"
    
    # Check reverse
    high_lower = last_10['high'].iloc[-1] < last_10['high'].iloc[:-1].max()
    low_lower = last_10['low'].iloc[-1] < last_10['low'].iloc[:-1].min()
    
    if high_lower and low_lower:
        return "bearish"
    
    # ========== METHOD 4: Close vs Open Bias ==========
    # Count bullish vs bearish candles in recent period
    bullish_candles = (recent['close'] > recent['open']).sum()
    bearish_candles = (recent['close'] < recent['open']).sum()
    
    ratio = bullish_candles / len(recent) if len(recent) > 0 else 0.5
    
    if ratio > 0.6:  # More than 60% bullish candles
        return "bullish"
    elif ratio < 0.4:  # More than 60% bearish candles
        return "bearish"
    
    # Default to range if no clear trend
    return "range"


def htf_trend_advanced(df: pd.DataFrame, lookback: int = 50, 
                       confidence_threshold: float = 0.7) -> Tuple[str, float]:
    """
    Advanced trend detection with confidence score
    
    Returns:
        Tuple: (trend, confidence)
        - trend: 'bullish', 'bearish', or 'range'
        - confidence: 0.0 to 1.0 (higher = stronger trend)
    """
    if len(df) < 20:
        return "range", 0.0
    
    recent = df.iloc[-lookback:].copy()
    
    # Score different trend indicators
    scores = {
        'bullish': 0.0,
        'bearish': 0.0,
        'range': 0.0,
    }
    
    # Score 1: Swing Structure (weight: 0.4)
    highs = find_swing_highs(recent, window=5)
    lows = find_swing_lows(recent, window=5)
    
    if len(highs) >= 2 and len(lows) >= 2:
        last_high = recent['high'].iloc[highs[-1]]
        prev_high = recent['high'].iloc[highs[-2]]
        last_low = recent['low'].iloc[lows[-1]]
        prev_low = recent['low'].iloc[lows[-2]]
        
        hh = last_high > prev_high
        hl = last_low > prev_low
        lh = last_high < prev_high
        ll = last_low < prev_low
        
        if hh and hl:
            scores['bullish'] += 0.4
        elif lh and ll:
            scores['bearish'] += 0.4
        else:
            scores['range'] += 0.2
    
    # Score 2: Moving Averages (weight: 0.3)
    sma_20 = recent['close'].rolling(window=20).mean()
    sma_50 = recent['close'].rolling(window=50).mean()
    
    current_close = recent['close'].iloc[-1]
    current_ma20 = sma_20.iloc[-1]
    current_ma50 = sma_50.iloc[-1]
    
    if current_close > current_ma20 > current_ma50:
        scores['bullish'] += 0.3
    elif current_close < current_ma20 < current_ma50:
        scores['bearish'] += 0.3
    else:
        scores['range'] += 0.15
    
    # Score 3: Candle Bias (weight: 0.3)
    bullish_candles = (recent['close'] > recent['open']).sum()
    ratio = bullish_candles / len(recent)
    
    if ratio > 0.6:
        scores['bullish'] += 0.3
    elif ratio < 0.4:
        scores['bearish'] += 0.3
    else:
        scores['range'] += 0.15
    
    # Determine trend and confidence
    max_score = max(scores.values())
    trend = max(scores, key=scores.get)
    confidence = max_score  # 0.0 to 1.0
    
    return trend, confidence


def bos(df: pd.DataFrame, trend: str, lookback: int = 20) -> bool:
    """
    Break of Structure - detect if current candle breaks previous structure
    For bullish: breaking above previous swing high
    For bearish: breaking below previous swing low
    """
    if len(df) < lookback + 5:
        return False
    
    recent = df.iloc[-lookback:].copy()
    current_high = df['high'].iloc[-1]
    current_low = df['low'].iloc[-1]
    
    if trend == "bullish":
        # Find previous structure - look for recent swing lows
        lows = find_swing_lows(recent, window=3)
        if len(lows) >= 2:
            # BOS if we're above previous swing high from earlier structure
            structure_high = df['high'].iloc[-lookback:-5].max()
            return current_high > structure_high
    
    elif trend == "bearish":
        # Find previous structure - look for recent swing highs
        highs = find_swing_highs(recent, window=3)
        if len(highs) >= 2:
            # BOS if we're below previous swing low from earlier structure
            structure_low = df['low'].iloc[-lookback:-5].min()
            return current_low < structure_low
    
    return False


def choch(df: pd.DataFrame, trend: str, lookback: int = 20) -> bool:
    """
    Change of Character - milder form of BOS
    Indicates weakening trend
    """
    if len(df) < lookback:
        return False
    
    recent = df.iloc[-lookback:].copy()
    
    if trend == "bullish":
        # Bullish CHoCH = recent lower low
        lows = find_swing_lows(recent, window=3)
        if len(lows) >= 2:
            return recent['low'].iloc[lows[-1]] < recent['low'].iloc[lows[-2]]
    
    elif trend == "bearish":
        # Bearish CHoCH = recent higher high
        highs = find_swing_highs(recent, window=3)
        if len(highs) >= 2:
            return recent['high'].iloc[highs[-1]] > recent['high'].iloc[highs[-2]]
    
    return False