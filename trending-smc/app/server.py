import grpc
import asyncio
from concurrent import futures
import logging
import sys
from typing import Optional

from proto import smc_pb2, smc_pb2_grpc
from app.market.fetcher import fetch_ohlcv
from app.strategy.smc_strategy import smc_strategy
from app.notification.telegram_handler import send_telegram_signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('grpc_server.log')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================

class TelegramConfig:
    """Telegram bot configuration"""
    BOT_TOKEN = "8260354429:AAF8xVrZuimJaxMbr43PtMZAAftwFKelXVE"      # Get from @BotFather
    CHAT_ID = "1912920643"          # Your chat ID
    ENABLE_NOTIFICATIONS = True
    DETAILED_MODE = True                    # Send detailed analysis
    
    @classmethod
    def validate(cls) -> bool:
        """Validate Telegram configuration"""
        if not cls.BOT_TOKEN:
            logger.warning("⚠️  Telegram BOT_TOKEN not configured")
            return False
        if not cls.CHAT_ID:
            logger.warning("⚠️  Telegram CHAT_ID not configured")
            return False
        return True


class StrategyConfig:
    """Strategy configuration - NOW RETURNS ALL CONFIDENCE GRADES"""
    SESSION_FILTER = None  # None, 'london', 'newyork', 'tokyo'
    MIN_CONFIDENCE = "C"   # Set to "C" to return ALL grades (A, B, C)
    DEBUG = True


# ============================================================================
# ASYNC TELEGRAM WRAPPER
# ============================================================================

async def send_signal_to_telegram_async(
    signal: dict,
    symbol: str,
    bot_token: str = TelegramConfig.BOT_TOKEN,
    chat_id: str = TelegramConfig.CHAT_ID,
) -> bool:
    """
    Send signal to Telegram asynchronously
    
    Args:
        signal: Signal dict from smc_strategy
        symbol: Trading symbol
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
    
    Returns:
        True if sent successfully
    """
    if not TelegramConfig.ENABLE_NOTIFICATIONS:
        logger.warning("⚠️  Telegram notifications disabled")
        return False
    
    if not TelegramConfig.validate():
        logger.warning("⚠️  Telegram not configured properly")
        return False
    
    try:
        logger.info(f"📤 Sending {symbol} signal to Telegram...")
        
        # Call async function
        await send_telegram_signal(
            signal=signal,
            symbol=symbol,
            chat_id=chat_id,
            bot_token=bot_token
        )
        
        logger.info(f"✅ Telegram notification sent for {symbol}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram notification: {e}")
        return False


def run_async_telegram(
    signal: dict,
    symbol: str,
    bot_token: str = TelegramConfig.BOT_TOKEN,
    chat_id: str = TelegramConfig.CHAT_ID,
) -> bool:
    """
    Run async telegram send from sync context (gRPC)
    
    Args:
        signal: Signal dict
        symbol: Trading symbol
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
    
    Returns:
        True if sent successfully
    """
    try:
        # Create new event loop for async operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            send_signal_to_telegram_async(signal, symbol, bot_token, chat_id)
        )
        
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ Error running async telegram: {e}")
        return False


# ============================================================================
# gRPC SERVICE
# ============================================================================

class SMCService(smc_pb2_grpc.SMCServiceServicer):
    """SMC Trading Service with Telegram Integration - Returns ALL Confidence Grades"""
    
    def Analyze(self, request, context):
        """
        Analyze symbol and send signal to Telegram
        NOW RETURNS ALL CONFIDENCE GRADES (A, B, C)
        
        Expected request payload:
        {
            "symbol": "BNBUSDT",
            "timeframe": "1h",
            "exchange": "binance" (optional),
            "limit": 200 (optional)
        }
        """
        logger.info("=" * 70)
        logger.info(f"📊 Received analysis request")
        logger.info(f"   Symbol: {request.symbol}")
        logger.info(f"   Timeframe: {request.timeframe}")
        
        # Get optional fields with defaults
        exchange = getattr(request, 'exchange', 'binance') or 'binance'
        limit = getattr(request, 'limit', 300) or 300
        
        logger.info(f"   Exchange: {exchange}")
        logger.info(f"   Limit: {limit}")
        logger.info(f"   Mode: 🎯 RETURNING ALL CONFIDENCE GRADES (A, B, C)")
        logger.info("=" * 70)
        
        try:
            # ========== STEP 1: Fetch Data ==========
            logger.info(f"[1] Fetching HTF data ({request.timeframe})...")
            htf_df = fetch_ohlcv(
                symbol=request.symbol,
                timeframe=request.timeframe,
                exchange_name=exchange,
                limit=300
            )
            
            if htf_df is None or len(htf_df) == 0:
                logger.warning("⚠️  HTF data fetch failed")
                logger.info("=" * 70)
                return smc_pb2.AnalyzeResponse()
            
            logger.info(f"✅ HTF data fetched ({len(htf_df)} candles)")
            
            logger.info(f"[2] Fetching LTF data ({request.timeframe})...")
            ltf_df = fetch_ohlcv(
                symbol=request.symbol,
                timeframe=request.timeframe,
                exchange_name=exchange,
                limit=300
            )
            
            if ltf_df is None or len(ltf_df) == 0:
                logger.warning("⚠️  LTF data fetch failed")
                logger.info("=" * 70)
                return smc_pb2.AnalyzeResponse()
            
            logger.info(f"✅ LTF data fetched ({len(ltf_df)} candles)")
            
            # ========== STEP 2: Run Strategy ==========
            logger.info(f"[3] Running SMC strategy (all confidence grades)...")
            signal = smc_strategy(
                htf_df=htf_df,
                ltf_df=ltf_df,
                debug=StrategyConfig.DEBUG,
                session_filter=StrategyConfig.SESSION_FILTER,
                min_confidence=StrategyConfig.MIN_CONFIDENCE  # "C" = all grades
            )
            
            if not signal:
                logger.info(f"⚠️  No signal found for {request.symbol}")
                logger.info("=" * 70)
                return smc_pb2.AnalyzeResponse()
            
            logger.info(f"✅ Signal generated for {request.symbol}")
            
            # ========== STEP 3: Build Response ==========
            logger.info(f"[4] Building response...")
            response = smc_pb2.AnalyzeResponse(
                symbol=request.symbol,
                timeframe=request.timeframe,
                side=signal["side"],
                entry_low=signal["entry"][0],
                entry_high=signal["entry"][1],
                stop_loss=signal["sl"],
                take_profit=signal["tp"],
                # confidence=signal.get("confidence", "C"),  # Include confidence grade
                # zone_type=signal.get("zone_type", "").upper(),  # Include zone type
                # zone_source=signal.get("zone_source", ""),  # Include zone source
            )
            
            logger.info(f"✅ Response built successfully")
            logger.info(f"   Side: {signal['side']}")
            logger.info(f"   Entry: {signal['entry'][0]:.2f} - {signal['entry'][1]:.2f}")
            logger.info(f"   SL: {signal['sl']:.2f}")
            logger.info(f"   TP: {signal['tp']:.2f}")
            logger.info(f"   Confidence Grade: ⭐ {signal.get('confidence', 'C')}")
            logger.info(f"   Zone Type: {signal.get('zone_type', 'N/A').upper()}")
            logger.info(f"   Zone Source: {signal.get('zone_source', 'N/A')}")
            logger.info(f"   Risk/Reward: 1:{signal.get('risk_reward', 0):.2f}")
            
            # ========== STEP 4: Send Telegram ==========
            logger.info(f"[5] Sending to Telegram...")
            telegram_sent = run_async_telegram(
                signal=signal,
                symbol=request.symbol,
                bot_token=TelegramConfig.BOT_TOKEN,
                chat_id=TelegramConfig.CHAT_ID,
            )
            
            if telegram_sent:
                logger.info(f"✅ Telegram notification sent")
            else:
                logger.warning(f"⚠️  Telegram notification failed (non-critical)")
            
            logger.info("=" * 70 + "\n")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {request.symbol}: {str(e)}", exc_info=True)
            logger.info("=" * 70 + "\n")
            context.set_details(f"Error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return smc_pb2.AnalyzeResponse()


# ============================================================================
# SERVER STARTUP
# ============================================================================

def serve(host: str = "0.0.0.0", port: int = 50051):
    """
    Start gRPC server
    
    Args:
        host: Server host
        port: Server port
    """
    logger.info("=" * 70)
    logger.info("🚀 SMC Trading Bot - gRPC Server")
    logger.info("=" * 70)
    
    # Validate Telegram configuration
    if not TelegramConfig.validate():
        logger.warning("⚠️  Telegram not configured - signals will not be sent")
        logger.warning("    Update TelegramConfig.BOT_TOKEN and CHAT_ID")
    else:
        logger.info("✅ Telegram configured - signals will be sent")
    
    logger.info(f"📋 Strategy Configuration:")
    logger.info(f"   Mode: 🎯 RETURN ALL CONFIDENCE GRADES (A, B, C)")
    logger.info(f"   Session Filter: {StrategyConfig.SESSION_FILTER or 'None (all sessions)'}")
    logger.info(f"   Min Confidence: {StrategyConfig.MIN_CONFIDENCE} (set to 'C' for all grades)")
    logger.info(f"   Debug Mode: {StrategyConfig.DEBUG}")
    logger.info("=" * 70)
    
    # Create and start server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    smc_pb2_grpc.add_SMCServiceServicer_to_server(
        SMCService(), server
    )
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    
    logger.info(f"✅ Server listening on {host}:{port}")
    logger.info("⏸️  Press Ctrl+C to stop...\n")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down server...")
        server.stop(grace=5)
        logger.info("✓ Server stopped")