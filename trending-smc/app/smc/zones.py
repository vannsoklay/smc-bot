import pandas as pd
from typing import Dict, List

def premium_discount(df: pd.DataFrame, lookback: int = 100) -> Dict:
    """
    Identify premium (resistance) and discount (support) zones
    Premium: Highest resistance area (top 2%)
    Discount: Lowest support area (bottom 2%)
    """
    recent = df.iloc[-lookback:].copy()
    
    highest = recent['high'].max()
    lowest = recent['low'].min()
    
    zones = {
        'premium': {
            'high': highest,
            'low': highest * 0.98,  # 2% buffer below highest
        },
        'discount': {
            'high': lowest * 1.02,  # 2% buffer above lowest
            'low': lowest,
        }
    }
    
    return zones


def price_zone(price: float, zones: Dict) -> str:
    """
    Determine if price is in premium or discount zone
    Returns: 'premium', 'discount', or 'neutral'
    """
    premium = zones['premium']
    discount = zones['discount']
    
    if premium['low'] <= price <= premium['high']:
        return "premium"
    elif discount['low'] <= price <= discount['high']:
        return "discount"
    else:
        return "neutral"