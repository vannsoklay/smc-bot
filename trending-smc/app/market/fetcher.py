import ccxt
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

# Initialize exchanges
exchanges = {
    "binance": ccxt.binance(),
    "bybit": ccxt.bybit()
}

def fetch_ohlcv(symbol: str, timeframe: str = "1h", exchange_name: str = "binance",
                limit: int = 200, retries: int = 3, sleep_time: float = 1.0) -> pd.DataFrame:
    """
    Fetch OHLCV data from exchange and return as Pandas DataFrame.

    Args:
        symbol: Trading pair like "BTC/USDT"
        timeframe: "1m", "5m", "15m", "1h", "4h", "1d"
        exchange_name: "binance" or "bybit"
        limit: Number of candles
        retries: Retry times in case of network issues
        sleep_time: Seconds to wait between retries

    Returns:
        Pandas DataFrame with columns: ["time","open","high","low","close","volume"]
    """
    if exchange_name not in exchanges:
        raise ValueError(f"Exchange '{exchange_name}' not supported")

    exchange = exchanges[exchange_name]

    attempt = 0
    while attempt < retries:
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not data:
                raise ValueError("Empty OHLCV data returned")

            df = pd.DataFrame(data, columns=["time","open","high","low","close","volume"])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df

        except Exception as e:
            attempt += 1
            logger.warning(f"Fetch attempt {attempt}/{retries} failed for {symbol} on {exchange_name}: {e}")
            time.sleep(sleep_time)

    logger.error(f"❌ Failed to fetch OHLCV for {symbol} after {retries} attempts")
    return pd.DataFrame()  # return empty dataframe if all retries fail
