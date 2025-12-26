"""
Helper functions for SMC strategy improvements
- Confidence scoring
- Session filtering
- Signal deduplication
"""

from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime


def get_trading_session(timestamp, timezone: str = "Asia/Bangkok") -> str:
    """
    Determine trading session based on hour (UTC)
    
    Args:
        timestamp: pandas Timestamp, datetime object, or any object with hour attribute
        timezone: Timezone of the timestamp ('UTC', 'Asia/Bangkok', etc.)
    
    Returns:
        'london', 'newyork', 'tokyo', or 'none'
    """
    try:
        # Handle different input types
        if isinstance(timestamp, pd.Timestamp):
            ts = timestamp
        elif isinstance(timestamp, datetime):
            ts = pd.Timestamp(timestamp)
        elif hasattr(timestamp, 'hour'):
            ts = pd.Timestamp(timestamp)
        else:
            ts = pd.Timestamp(timestamp)
        
        # Convert to UTC if needed
        if timezone and timezone != "UTC":
            try:
                # Localize to given timezone, then convert to UTC
                if ts.tz is None:
                    ts = ts.tz_localize(timezone)
                ts = ts.tz_convert('UTC')
            except Exception as tz_error:
                print(f"⚠️  Could not convert timezone: {tz_error}")
                # Continue with local time if conversion fails
        
        hour = ts.hour
        
        # Determine session based on UTC hour
        if 8 <= hour < 16:
            return "london"
        elif 13 <= hour < 21:
            return "newyork"
        elif 0 <= hour < 8:
            return "tokyo"
        else:
            return "none"
    
    except Exception as e:
        print(f"⚠️  Error parsing timestamp: {e}")
        print(f"   Timestamp type: {type(timestamp)}")
        print(f"   Timestamp value: {timestamp}")
        return "none"


def calculate_zone_strength(price: float, zone: Dict) -> float:
    """
    Calculate how strong the zone is (0.0 to 1.0)
    Closer to middle of zone = stronger
    
    Args:
        price: Current price
        zone: Dict with 'high' and 'low' keys
    
    Returns:
        Float between 0.0 and 1.0 (1.0 = strongest)
    """
    try:
        zone_range = float(zone['high']) - float(zone['low'])
        if zone_range == 0:
            return 0.5
        
        # Distance from edges (1.0 = middle, 0.0 = edge)
        dist_from_low = float(price) - float(zone['low'])
        position_ratio = dist_from_low / zone_range
        
        # Middle is strongest (0.5), edges are weaker
        strength = 1.0 - abs(position_ratio - 0.5) * 2
        return max(0.0, min(1.0, strength))
    
    except Exception as e:
        print(f"⚠️  Error calculating zone strength: {e}")
        return 0.5


def calculate_confidence_score(ls_check: bool, bos_check: bool, 
                               zone_strength: float) -> str:
    """
    Calculate confidence grade: A, B, or C
    
    A Grade: All conditions met + strong zone (2 checks + strength > 0.7)
    B Grade: 2 conditions met OR strength > 0.7
    C Grade: 1 condition met (lowest confidence)
    
    Args:
        ls_check: Liquidity sweep detected (True/False)
        bos_check: Break of structure detected (True/False)
        zone_strength: Zone strength score (0.0-1.0)
    
    Returns:
        'A', 'B', or 'C'
    """
    try:
        conditions_met = sum([ls_check, bos_check])
        
        if conditions_met == 2 and zone_strength > 0.7:
            return "A"
        elif conditions_met == 2 or zone_strength > 0.7:
            return "B"
        else:
            return "C"
    
    except Exception as e:
        print(f"⚠️  Error calculating confidence: {e}")
        return "C"


def deduplicate_signals(zones_combined: List[Dict], price: float) -> Tuple[Dict, str, str]:
    """
    Find the best zone to trade (avoid duplicates)
    Prioritizes FVG over OB when both overlap
    
    Args:
        zones_combined: List of order blocks + FVGs
        price: Current price
    
    Returns:
        Tuple: (best_zone, zone_source, dedup_id)
        - best_zone: Dict with 'high', 'low' keys (or None)
        - zone_source: 'OB', 'FVG', 'BOTH', or 'NONE'
        - dedup_id: Unique signal ID (e.g., 'FVG_1' or 'FVG_1+OB_2')
    """
    try:
        obs = [z for z in zones_combined if 'ob_id' in z]
        fvgs = [z for z in zones_combined if 'fvg_id' in z]
        
        # Find which zones contain the price
        price_in_ob = None
        price_in_fvg = None
        
        for ob in obs:
            try:
                if float(ob['low']) <= float(price) <= float(ob['high']):
                    price_in_ob = ob
                    break
            except (ValueError, TypeError):
                continue
        
        for fvg in fvgs:
            try:
                if float(fvg['low']) <= float(price) <= float(fvg['high']):
                    price_in_fvg = fvg
                    break
            except (ValueError, TypeError):
                continue
        
        # Prioritize based on strength and type
        if price_in_ob and price_in_fvg:
            # Both OB and FVG - very strong (BOTH)
            dedup_id = f"{price_in_fvg.get('fvg_id', 'FVG_X')}+{price_in_ob.get('ob_id', 'OB_X')}"
            return price_in_fvg, "BOTH", dedup_id
        
        elif price_in_ob:
            dedup_id = price_in_ob.get('ob_id', 'OB_X')
            return price_in_ob, "OB", dedup_id
        
        elif price_in_fvg:
            dedup_id = price_in_fvg.get('fvg_id', 'FVG_X')
            return price_in_fvg, "FVG", dedup_id
        
        return None, "NONE", "NONE"
    
    except Exception as e:
        print(f"⚠️  Error deduplicating signals: {e}")
        return None, "NONE", "NONE"


def filter_by_confidence(confidence: str, min_confidence: str) -> bool:
    """
    Check if confidence grade meets minimum threshold
    
    Args:
        confidence: Current signal confidence ('A', 'B', or 'C')
        min_confidence: Minimum required confidence ('A', 'B', or 'C')
    
    Returns:
        True if confidence meets threshold
    """
    try:
        confidence_rank = {"A": 3, "B": 2, "C": 1}
        min_rank = confidence_rank.get(min_confidence, 1)
        signal_rank = confidence_rank.get(confidence, 1)
        
        return signal_rank >= min_rank
    
    except Exception as e:
        print(f"⚠️  Error filtering by confidence: {e}")
        return True


def format_signal_output(side: str, price: float, sl: float, tp: float,
                        trend: str, zone_type: str, zone_source: str,
                        dedup_id: str, confidence: str, zone_strength: float) -> Dict:
    """
    Format the final trading signal with all data
    
    Returns:
        Complete signal dictionary ready for trading
    """
    try:
        risk = abs(float(price) - float(sl))
        reward = abs(float(tp) - float(price))
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            "side": side,
            "entry": (round(float(price), 2), round(float(price), 2)),
            "sl": round(float(sl), 2),
            "tp": round(float(tp), 2),
            "trend": trend,
            "zone_type": zone_type,
            "zone_source": zone_source,
            "dedup_id": dedup_id,
            "confidence": confidence,
            "zone_strength": round(float(zone_strength), 2),
            "risk_reward": round(rr_ratio, 2),
        }
    
    except Exception as e:
        print(f"⚠️  Error formatting signal output: {e}")
        return {}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value, default: bool = False) -> bool:
    """Safely convert value to bool"""
    try:
        if isinstance(value, bool):
            return value
        return bool(value)
    except (ValueError, TypeError):
        return default