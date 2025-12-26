import logging
from telegram import Bot
from telegram.error import TelegramError
from app.notification.telegram_formatter import format_signal_for_telegram

async def send_telegram_signal(signal: dict, symbol: str, chat_id: str, bot_token: str):
    """Send signal to Telegram"""
    try:
        bot = Bot(token=bot_token)
        message = format_signal_for_telegram(signal, symbol)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        logging.info(f"✅ Signal sent to Telegram: {symbol}")
    except TelegramError as e:
        logging.error(f"❌ Telegram error: {e}")