from app.smc.structure import htf_trend, htf_trend_advanced, bos
from app.smc.liquidity import liquidity_sweep
from app.smc.orderblock import order_blocks
from app.smc.fvg import fair_value_gaps
from app.smc.zones import premium_discount, price_zone
from app.smc.helpers import (
    get_trading_session,
    calculate_zone_strength,
    calculate_confidence_score,
    deduplicate_signals,
    filter_by_confidence,
    format_signal_output,
)
import logging

logger = logging.getLogger(__name__)


def smc_strategy(htf_df, ltf_df, debug=False, session_filter="newyork", min_confidence="C"):
    """
    Complete SMC Strategy - Returns ALL confidence grades (A, B, C)
    
    Args:
        htf_df: Higher timeframe DataFrame (4H, 1D)
        ltf_df: Lower timeframe DataFrame (15m, 1H)
        debug: Print debug information (True/False)
        session_filter: 'london', 'newyork', 'tokyo', or None (no filter)
        min_confidence: Minimum confidence grade ('A', 'B', or 'C')
    
    Returns:
        Signal dict or None
    """
    
    try:
        # ========== STEP 1: Data Validation ==========
        if htf_df is None or ltf_df is None:
            logger.error("❌ Invalid dataframes")
            return None
        
        if len(htf_df) < 50 or len(ltf_df) < 20:
            logger.error(f"❌ Insufficient data: HTF={len(htf_df)}, LTF={len(ltf_df)}")
            return None
        
        if debug:
            print(f"✅ Data validation passed (HTF: {len(htf_df)}, LTF: {len(ltf_df)})")
        
        # ========== STEP 2: Identify HTF Trend ==========
        trend, trend_strength = htf_trend_advanced(htf_df, lookback=50)
        
        if debug:
            print(f"\n[1] HTF Trend Analysis")
            print(f"    Trend: {trend.upper()}")
            print(f"    Strength: {trend_strength:.0%}")
        
        # Allow range with low confidence (optional)
        if trend == "range":
            if debug:
                print(f"    ⚠️  Market in range (weak trend)")
            # Option 1: Skip range markets
            if trend_strength < 0.5:
                if debug:
                    print(f"    ❌ Trend strength {trend_strength:.0%} too weak, skipping")
                return None
            # Option 2: Continue with lower confidence grade
        
        # ========== STEP 3: Session Filter ==========
        session_ok = True
        current_session = "unknown"
        
        if session_filter:
            try:
                current_time = ltf_df.index[-1]
                current_session = get_trading_session(current_time)
                
                if debug:
                    print(f"\n[2] Session Filter")
                    print(f"    Current Session (UTC): {current_session}")
                    print(f"    Filter: {session_filter}")
                
                if current_session != session_filter:
                    if debug:
                        print(f"    ❌ Not in {session_filter} session, skipping")
                    return None
                else:
                    if debug:
                        print(f"    ✅ In {session_filter} session")
            except Exception as e:
                logger.warning(f"⚠️  Session filter error: {e}")
                if debug:
                    print(f"    ⚠️  Could not determine session, continuing anyway")
        else:
            if debug:
                print(f"\n[2] No session filter (trading all times)")
        
        # ========== STEP 4: Premium/Discount Zones ==========
        zones = premium_discount(htf_df, lookback=100)
        price = float(ltf_df['close'].iloc[-1])
        zone_type = price_zone(price, zones)
        
        if debug:
            print(f"\n[3] Zone Analysis")
            print(f"    Current Price: {price:.2f}")
            print(f"    Zone Type: {zone_type.upper()}")
            print(f"    Premium Zone: {zones['premium']['low']:.2f} - {zones['premium']['high']:.2f}")
            print(f"    Discount Zone: {zones['discount']['low']:.2f} - {zones['discount']['high']:.2f}")
        
        # ========== STEP 5: Find Order Blocks and FVGs ==========
        obs = order_blocks(htf_df, trend, lookback=50)
        fvgs = fair_value_gaps(htf_df, trend, lookback=50)
        
        if debug:
            print(f"\n[4] Market Structure")
            print(f"    Order Blocks Found: {len(obs)}")
            if obs:
                for ob in obs[:3]:  # Show first 3
                    print(f"        └─ {ob.get('ob_id', 'OB')}: {ob['low']:.2f} - {ob['high']:.2f}")
            print(f"    Fair Value Gaps: {len(fvgs)}")
            if fvgs:
                for fvg in fvgs[:3]:  # Show first 3
                    print(f"        └─ {fvg.get('fvg_id', 'FVG')}: {fvg['low']:.2f} - {fvg['high']:.2f}")
        
        zones_combined = obs + fvgs
        
        if not zones_combined:
            if debug:
                print(f"    ❌ No OBs or FVGs found")
            return None
        
        # ========== STEP 6: Signal Deduplication ==========
        price_in_zone, zone_source, dedup_id = deduplicate_signals(zones_combined, price)
        
        if not price_in_zone:
            if debug:
                print(f"\n[5] Zone Matching")
                print(f"    ❌ Price {price:.2f} not in any zone")
                # Show closest zones for debugging
                closest_dist = float('inf')
                closest_zone = None
                for z in zones_combined:
                    z_mid = (z['low'] + z['high']) / 2
                    dist = abs(price - z_mid)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_zone = z
                if closest_zone:
                    print(f"    Closest zone: {closest_zone['low']:.2f} - {closest_zone['high']:.2f} ({closest_dist:.2f} away)")
            return None
        
        if debug:
            print(f"\n[5] Zone Matching")
            print(f"    ✅ Price in zone ({zone_source})")
            print(f"    Zone ID: {dedup_id}")
            print(f"    Zone Range: {price_in_zone['low']:.2f} - {price_in_zone['high']:.2f}")
        
        # ========== STEP 7: Liquidity & Structure Confirmation ==========
        ls_check = liquidity_sweep(ltf_df, trend)
        bos_check = bos(ltf_df, trend)
        
        if debug:
            print(f"\n[6] Confirmation Signals")
            print(f"    Liquidity Sweep: {'✅' if ls_check else '❌'}")
            print(f"    Break of Structure: {'✅' if bos_check else '❌'}")
        
        # ========== STEP 8: Calculate Confidence Score ==========
        zone_strength = calculate_zone_strength(price, price_in_zone)
        confidence = calculate_confidence_score(ls_check, bos_check, zone_strength)
        
        if debug:
            print(f"\n[7] Confidence Scoring")
            print(f"    Zone Strength: {zone_strength:.0%}")
            print(f"    Confidence Grade: {confidence}")
            print(f"    └─ Liquidity: {ls_check}, Structure: {bos_check}, Strength: {zone_strength:.0%}")
        
        # ========== STEP 9: REMOVED - No longer filter by confidence ==========
        # Now we accept ALL confidence grades (A, B, C)
        # Remove this check to return all signals regardless of confidence
        # if not filter_by_confidence(confidence, min_confidence):
        #     if debug:
        #         print(f"\n[8] Confidence Filter")
        #         print(f"    ❌ Grade {confidence} below minimum {min_confidence}")
        #     return None
        
        if debug:
            print(f"\n[8] Confidence Grade")
            print(f"    ✅ Returning signal with Grade {confidence}")
        
        # ========== STEP 10: Generate Trade Signal ==========
        if trend == "bullish":
            sl = price_in_zone['low']
            tp = price + (price - sl) * 3
            side = "BUY"
        else:  # bearish
            sl = price_in_zone['high']
            tp = price - (sl - price) * 3
            side = "SELL"
        
        # ========== STEP 11: Format Final Signal ==========
        signal = format_signal_output(
            side=side,
            price=price,
            sl=sl,
            tp=tp,
            trend=trend,
            zone_type=zone_type,
            zone_source=zone_source,
            dedup_id=dedup_id,
            confidence=confidence,
            zone_strength=zone_strength,
        )
        
        # Add extra data
        signal['trend_strength'] = trend_strength
        signal['session'] = current_session
        
        if debug:
            print(f"\n{'='*70}")
            print(f"✅ SIGNAL GENERATED SUCCESSFULLY")
            print(f"{'='*70}")
            print(f"Side:              {signal['side']}")
            print(f"Entry:             {signal['entry'][0]:.2f}")
            print(f"Stop Loss:         {signal['sl']:.2f}")
            print(f"Take Profit:       {signal['tp']:.2f}")
            print(f"Risk/Reward:       1:{signal['risk_reward']:.2f}")
            print(f"Confidence:        {signal['confidence']} Grade")
            print(f"Trend Strength:    {signal['trend_strength']:.0%}")
            print(f"Zone Source:       {signal['zone_source']} ({signal['dedup_id']})")
            print(f"Zone Strength:     {signal['zone_strength']:.0%}")
            print(f"{'='*70}\n")
        
        logger.info(f"✅ Signal generated: {signal['side']} at {signal['entry'][0]:.2f} (Grade: {confidence})")
        return signal
        
    except Exception as e:
        logger.error(f"❌ Strategy error: {str(e)}", exc_info=True)
        if debug:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        return None


# ============================================================================
# QUICK TEST FUNCTION
# ============================================================================

def test_strategy(htf_df, ltf_df):
    """Quick test with all parameters - Now returns ALL grades"""
    print("\n" + "="*70)
    print("Testing SMC Strategy - All Confidence Grades (A, B, C)")
    print("="*70)
    
    # Test 1: All signals, all grades
    print("\n📊 Test 1: All signals (no filters, all confidence grades)")
    signal = smc_strategy(htf_df, ltf_df, debug=True, session_filter=None, min_confidence="C")
    
    # Test 2: London session only, all grades
    print("\n📊 Test 2: London session only (all confidence grades)")
    signal = smc_strategy(htf_df, ltf_df, debug=True, session_filter="london", min_confidence="C")
    
    # Test 3: All signals, all grades
    print("\n📊 Test 3: All signals, all grades (Grade A, B, and C)")
    signal = smc_strategy(htf_df, ltf_df, debug=True, session_filter=None, min_confidence="C")
    
    return signal