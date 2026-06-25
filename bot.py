import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# Test with just 3 stocks
test_symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
date_str = now.strftime("%d %B %Y, %I:%M %p")

message = f"<b>🧪 DATA TEST REPORT</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"

for symbol in test_symbols:
    try:
        message += f"<b>{symbol}:</b>\n"
        
        # Try download
        df = yf.download(symbol, period="5d", interval="1d", progress=False)
        message += f"  Rows downloaded: {len(df)}\n"
        
        if len(df) > 0:
            latest = df.iloc[-1]
            message += f"  Close: ₹{latest['Close']:.2f}\n"
            message += f"  High: ₹{latest['High']:.2f}\n"
            message += f"  Low: ₹{latest['Low']:.2f}\n"
            message += f"  Volume: {latest['Volume']:.0f}\n"
            message += f"  Columns: {list(df.columns)}\n"
        else:
            message += f"  ❌ EMPTY DATAFRAME\n"
        
        message += "\n"
    except Exception as e:
        message += f"  ❌ ERROR: {str(e)[:200]}\n\n"

message += "━━━━━━━━━━━━━━━\nCheck if data is coming through."

send_telegram(message)
