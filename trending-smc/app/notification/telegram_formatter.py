"""
Format SMC trading signals for Telegram messages
"""

from typing import Dict, List
from datetime import datetime


def format_signal_for_telegram(signal: Dict, symbol: str) -> str:
    """
    Format a single trading signal for Telegram
    
    Args:
        signal: Signal dict from smc_strategy()
        symbol: Trading symbol (e.g., 'BNBUSDT', 'BTCUSDT')
    
    Returns:
        Formatted message string for Telegram
    """
    
    # Emoji and symbols
    emoji_side = "🟢 BUY" if signal['side'] == "BUY" else "🔴 SELL"
    emoji_confidence = {
        "A": "🟢",  # Green
        "B": "🟡",  # Yellow
        "C": "🟠"   # Orange
    }.get(signal['confidence'], "⚪")
    
    emoji_zone = {
        "OB": "🧱",     # Order Block
        "FVG": "⬜",     # Fair Value Gap
        "BOTH": "⭐",    # Both (strongest)
        "NONE": "❓"
    }.get(signal['zone_source'], "❓")
    
    emoji_trend = "📈" if signal['trend'] == "bullish" else "📉"
    
    # Calculate risk/reward
    entry = signal['entry'][0]
    sl = signal['sl']
    tp = signal['tp']
    
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr_ratio = reward / risk if risk > 0 else 0
    
    # Build message
    message = f"""
╔════════════════════════════════════════╗
║        🎯 SMC TRADING SIGNAL 🎯        ║
╚════════════════════════════════════════╝

📊 Symbol: {symbol}
{emoji_side}
{emoji_trend} Trend: {signal['trend'].upper()}
{emoji_confidence} Confidence: {signal['confidence']} Grade
{emoji_zone} Source: {signal['zone_source']} ({signal['dedup_id']})

════════════════════════════════════════

💰 ENTRY
   └─ Price: {entry:.2f}

🛑 STOP LOSS
   └─ Price: {sl:.2f}
   └─ Risk: {risk:.2f}

🎯 TAKE PROFIT
   └─ Price: {tp:.2f}
   └─ Reward: {reward:.2f}

📈 RISK/REWARD: 1:{rr_ratio:.2f}

════════════════════════════════════════

📍 Zone Details:
   └─ Type: {signal['zone_type'].upper()}
   └─ Strength: {signal['zone_strength']:.0%}

════════════════════════════════════════

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

════════════════════════════════════════
"""
    
    return message


def format_multiple_signals_for_telegram(signals: List[Dict], symbols: List[str]) -> str:
    """
    Format multiple signals for a single Telegram message
    
    Args:
        signals: List of signal dicts
        symbols: List of symbols corresponding to each signal
    
    Returns:
        Formatted message with all signals
    """
    
    if not signals:
        return "❌ No trading signals generated at this time"
    
    # Group by confidence
    signals_by_confidence = {"A": [], "B": [], "C": []}
    
    for signal, symbol in zip(signals, symbols):
        confidence = signal['confidence']
        signals_by_confidence[confidence].append((signal, symbol))
    
    # Start message
    message = f"""
╔════════════════════════════════════════╗
║   📊 MARKET ANALYSIS SUMMARY 📊        ║
╚════════════════════════════════════════╝

⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📈 Total Signals: {len(signals)}

════════════════════════════════════════
"""
    
    # A Grade Signals (Best)
    if signals_by_confidence["A"]:
        message += f"\n🟢 GRADE A - BEST SIGNALS ({len(signals_by_confidence['A'])})\n"
        message += "─" * 40 + "\n"
        for signal, symbol in signals_by_confidence["A"]:
            message += f"✅ {symbol:10} | {signal['side']:4} | RR 1:{signal['risk_reward']:.2f}\n"
    
    # B Grade Signals (Medium)
    if signals_by_confidence["B"]:
        message += f"\n🟡 GRADE B - MEDIUM SIGNALS ({len(signals_by_confidence['B'])})\n"
        message += "─" * 40 + "\n"
        for signal, symbol in signals_by_confidence["B"]:
            message += f"⚠️  {symbol:10} | {signal['side']:4} | RR 1:{signal['risk_reward']:.2f}\n"
    
    # C Grade Signals (Low)
    if signals_by_confidence["C"]:
        message += f"\n🟠 GRADE C - LOW SIGNALS ({len(signals_by_confidence['C'])})\n"
        message += "─" * 40 + "\n"
        for signal, symbol in signals_by_confidence["C"]:
            message += f"⏸️  {symbol:10} | {signal['side']:4} | RR 1:{signal['risk_reward']:.2f}\n"
    
    message += f"""
════════════════════════════════════════

📊 STATISTICS
   └─ A Grade: {len(signals_by_confidence['A'])}
   └─ B Grade: {len(signals_by_confidence['B'])}
   └─ C Grade: {len(signals_by_confidence['C'])}

════════════════════════════════════════
"""
    
    return message


def format_detailed_signal_for_telegram(signal: Dict, symbol: str, 
                                       ltf_data: str = None) -> str:
    """
    Format detailed signal with extra analysis
    
    Args:
        signal: Signal dict
        symbol: Trading symbol
        ltf_data: Optional LTF analysis text
    
    Returns:
        Detailed formatted message
    """
    
    entry = signal['entry'][0]
    sl = signal['sl']
    tp = signal['tp']
    
    # Calculate positions
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    
    message = f"""
╔════════════════════════════════════════╗
║      📈 DETAILED SIGNAL ANALYSIS 📈    ║
╚════════════════════════════════════════╝

📊 {symbol}
{'🟢 BUY' if signal['side'] == 'BUY' else '🔴 SELL'} | {signal['trend'].upper()}

════════════════════════════════════════

🎯 TRADING PLAN

Entry Zone: {entry:.2f}
Stop Loss:  {sl:.2f}
Take Prof:  {tp:.2f}

Risk Per Trade: {risk:.2f}
Reward Target:  {reward:.2f}
R:R Ratio:      1:{reward/risk:.2f}

════════════════════════════════════════

📍 ZONE ANALYSIS

Source: {signal['zone_source']} ({signal['dedup_id']})
Type:   {signal['zone_type'].upper()}
Strength: {"█" * int(signal['zone_strength'] * 10)}{"░" * (10 - int(signal['zone_strength'] * 10))} {signal['zone_strength']:.0%}

════════════════════════════════════════

⭐ SIGNAL QUALITY

Confidence:     {signal['confidence']} Grade
Zone Strength:  {signal['zone_strength']:.0%}

════════════════════════════════════════

💡 TRADING RULES

1. Enter on zone bounce
2. SL at zone edge ({signal['zone_type']})
3. TP at 3x risk target
4. Risk only 1-2% per trade
5. Always use stop loss

════════════════════════════════════════

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Confidence: {signal['confidence']}

════════════════════════════════════════
"""
    
    if ltf_data:
        message += f"\n📊 LTF Analysis:\n{ltf_data}\n"
    
    return message


def format_summary_stats(all_signals: List[Dict]) -> str:
    """
    Format overall market summary statistics
    
    Args:
        all_signals: List of all signals
    
    Returns:
        Summary statistics message
    """
    
    if not all_signals:
        return "❌ No signals to analyze"
    
    total = len(all_signals)
    buys = sum(1 for s in all_signals if s['side'] == 'BUY')
    sells = sum(1 for s in all_signals if s['side'] == 'SELL')
    
    bullish = sum(1 for s in all_signals if s['trend'] == 'bullish')
    bearish = sum(1 for s in all_signals if s['trend'] == 'bearish')
    
    grade_a = sum(1 for s in all_signals if s['confidence'] == 'A')
    grade_b = sum(1 for s in all_signals if s['confidence'] == 'B')
    grade_c = sum(1 for s in all_signals if s['confidence'] == 'C')
    
    avg_rr = sum(s['risk_reward'] for s in all_signals) / total if total > 0 else 0
    
    message = f"""
╔════════════════════════════════════════╗
║     📊 MARKET SUMMARY STATISTICS 📊    ║
╚════════════════════════════════════════╝

📈 SIGNAL COUNTS
   Total Signals: {total}
   └─ BUY:  🟢 {buys}
   └─ SELL: 🔴 {sells}

📊 TREND BREAKDOWN
   Bullish:  📈 {bullish}
   Bearish:  📉 {bearish}

⭐ CONFIDENCE DISTRIBUTION
   A Grade (Best):    🟢 {grade_a}
   B Grade (Medium):  🟡 {grade_b}
   C Grade (Low):     🟠 {grade_c}

💰 RISK/REWARD METRICS
   Average R:R: 1:{avg_rr:.2f}
   Best R:R:    1:{max(s['risk_reward'] for s in all_signals):.2f}
   Worst R:R:   1:{min(s['risk_reward'] for s in all_signals):.2f}

════════════════════════════════════════

⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

════════════════════════════════════════
"""
    
    return message
