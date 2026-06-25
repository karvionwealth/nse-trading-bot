import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# ---------- CONFIG ----------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Indian stock universe (add more for better coverage)
SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "WIPRO.NS",
    "HCLTECH.NS", "ULTRACEMCO.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "ADANIPORTS.NS", "ADANIENT.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "CIPLA.NS", "BRITANNIA.NS", "HDFCLIFE.NS", "SBILIFE.NS",
    "EICHERMOT.NS", "M&M.NS", "TATAMOTORS.NS", "HINDZINC.NS",
    "VEDL.NS", "DLF.NS", "INDIGO.NS", "HAVELLS.NS", "VOLTAS.NS",
    "DABUR.NS", "PIDILITIND.NS", "BERGEPAINT.NS", "LUPIN.NS",
    "AUROPHARMA.NS", "BIOCON.NS", "TORNTPHARM.NS", "ALKEM.NS"
]

# ---------- TELEGRAM ----------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ---------- INDICATORS (manual, no pandas-ta) ----------
def compute_indicators(df):
    """Add EMA, ATR, RSI, volume avg, and 20-day high to dataframe."""
    # EMAs
    df['ema20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # ATR (14)
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volume average (20)
    df['vol_avg20'] = df['Volume'].rolling(20).mean()

    # 20-day rolling high
    df['high20'] = df['High'].rolling(20).max()

    return df

# ---------- MAIN SCANNER ----------
def find_breakout_candidates():
    """Scan all symbols using yesterday's completed daily candle."""
    candidates = []
    for symbol in SYMBOLS:
        try:
            # Download 90 days of daily data (enough for indicators)
            df = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if len(df) < 60:
                continue

            # Compute indicators
            df = compute_indicators(df)

            # Use the last completed row (yesterday's data)
            today = df.iloc[-1]
            yesterday = df.iloc[-2]

            # --- Conditions ---
            # 1. Price within 2% of 20-day high (breakout zone)
            near_high = today['Close'] >= today['high20'] * 0.98

            # 2. Uptrend: ema20 > ema50
            uptrend = today['ema20'] > today['ema50']

            # 3. RSI between 50 and 70 (not overbought but momentum)
            rsi_ok = 50 < today['rsi'] < 70

            # 4. Volume spike: yesterday's volume > 1.5× average
            volume_surge = today['Volume'] > 1.5 * today['vol_avg20']

            # 5. Higher lows in last 10 days vs prior 10 days
            higher_lows = df['Low'].iloc[-10:].min() > df['Low'].iloc[-20:-10].min()

            if near_high and uptrend and rsi_ok and volume_surge and higher_lows:
                # Trigger = 0.5% above the 20-day high (buy-stop)
                trigger = round(today['high20'] * 1.005, 2)
                atr = round(today['atr'], 2)
                stop_loss = round(trigger - 2 * today['atr'], 2)
                target1 = round(trigger + 4 * today['atr'], 2)   # partial profit
                target2 = round(trigger + 6 * today['atr'], 2)   # final target

                candidates.append({
                    'symbol': symbol.replace('.NS', ''),
                    'trigger': trigger,
                    'sl': stop_loss,
                    'target1': target1,
                    'target2': target2,
                    'close': round(today['Close'], 2),
                    'atr': atr,
                    'volume_ratio': round(today['Volume'] / today['vol_avg20'], 1)
                })
        except Exception as e:
            print(f"Error {symbol}: {e}")
            continue
    return candidates

# ---------- DAILY REPORT ----------
def send_daily_report():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")

    candidates = find_breakout_candidates()

    if not candidates:
        message = f"<b>🔕 No breakout candidates today</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\nCriteria not met. Wait for next session."
        send_telegram(message)
        return

    # Build message
    message = f"<b>🔔 NSE BREAKOUT ALERTS</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"
    for c in candidates[:5]:  # Top 5 only to avoid clutter
        message += (
            f"📈 <b>{c['symbol']}</b>\n"
            f"  <b>Buy-Stop Trigger:</b> ₹{c['trigger']}\n"
            f"  Stop Loss: ₹{c['sl']} | Target 1: ₹{c['target1']} | Target 2: ₹{c['target2']}\n"
            f"  Last Close: ₹{c['close']} | ATR: ₹{c['atr']} | Vol: {c['volume_ratio']}x\n"
            f"━━━━━━━━━━━━━━━━\n"
        )
    message += "⚠️ Place <b>buy-stop</b> order above trigger for today. Valid only for this session."
    send_telegram(message)

if __name__ == "__main__":
    send_daily_report()
