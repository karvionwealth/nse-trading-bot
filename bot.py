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

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_value(series_or_scalar):
    """Safely extract a single float from a pandas object."""
    if isinstance(series_or_scalar, (pd.Series, np.ndarray)):
        return float(series_or_scalar.iloc[0] if len(series_or_scalar) > 0 else 0)
    return float(series_or_scalar)

def compute_indicators(df):
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    df['ema20'] = close.ewm(span=20, adjust=False).mean()
    df['ema50'] = close.ewm(span=50, adjust=False).mean()

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg20'] = volume.rolling(20).mean()
    df['high20'] = high.rolling(20).max()
    return df

def find_breakout_candidates():
    candidates = []
    stats = {'total': 0, 'near_high': 0, 'uptrend': 0, 'rsi_ok': 0, 'volume_surge': 0, 'higher_lows': 0}

    for symbol in SYMBOLS:
        try:
            df = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if len(df) < 60:
                continue

            df = compute_indicators(df)
            latest = df.iloc[-1]
            stats['total'] += 1

            # Extract values safely
            close_val = get_value(latest['Close'])
            high20_val = get_value(latest['high20'])
            ema20_val = get_value(latest['ema20'])
            ema50_val = get_value(latest['ema50'])
            rsi_val = get_value(latest['rsi'])
            vol_val = get_value(latest['Volume'])
            vol_avg_val = get_value(latest['vol_avg20'])
            atr_val = get_value(latest['atr'])

            # Check conditions
            near_high = close_val >= high20_val * 0.98
            uptrend = ema20_val > ema50_val
            rsi_ok = 50 < rsi_val < 70
            volume_surge = vol_val > 1.5 * vol_avg_val
            higher_lows = df['Low'].iloc[-10:].min() > df['Low'].iloc[-20:-10].min()

            if near_high: stats['near_high'] += 1
            if uptrend: stats['uptrend'] += 1
            if rsi_ok: stats['rsi_ok'] += 1
            if volume_surge: stats['volume_surge'] += 1
            if higher_lows: stats['higher_lows'] += 1

            if near_high and uptrend and rsi_ok and volume_surge and higher_lows:
                trigger = round(high20_val * 1.005, 2)
                stop_loss = round(trigger - 2 * atr_val, 2)
                target1 = round(trigger + 4 * atr_val, 2)
                target2 = round(trigger + 6 * atr_val, 2)

                candidates.append({
                    'symbol': symbol.replace('.NS', ''),
                    'trigger': trigger,
                    'sl': stop_loss,
                    'target1': target1,
                    'target2': target2,
                    'close': round(close_val, 2),
                    'atr': round(atr_val, 2),
                    'volume_ratio': round(vol_val / vol_avg_val, 1)
                })
        except Exception as e:
            print(f"Error {symbol}: {e}")
            continue

    return candidates, stats

def send_daily_report():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")

    candidates, stats = find_breakout_candidates()

    message = f"<b>📊 NSE SCAN REPORT</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"
    message += f"<b>Stocks Scanned:</b> {stats['total']}\n\n"
    message += "<b>Filters Passed:</b>\n"
    message += f"• Near 20d High: {stats['near_high']}\n"
    message += f"• Uptrend (EMA): {stats['uptrend']}\n"
    message += f"• RSI 50-70: {stats['rsi_ok']}\n"
    message += f"• Volume Surge 1.5x: {stats['volume_surge']}\n"
    message += f"• Higher Lows: {stats['higher_lows']}\n"
    message += f"━━━━━━━━━━━━━━━\n\n"

    if candidates:
        message += f"<b>🔥 BREAKOUT CANDIDATES: {len(candidates)}</b>\n\n"
        for c in candidates[:5]:
            message += (
                f"📈 <b>{c['symbol']}</b>\n"
                f"  Trigger: ₹{c['trigger']}\n"
                f"  SL: ₹{c['sl']} | T1: ₹{c['target1']} | T2: ₹{c['target2']}\n"
                f"  Close: ₹{c['close']} | ATR: ₹{c['atr']} | Vol: {c['volume_ratio']}x\n"
                f"━━━━━━━━━━━━━━━━\n"
            )
        message += "⚠️ Place buy-stop order above trigger for today."
    else:
        message += "🔕 No stocks passed all 5 filters.\n"
        total = max(stats['total'], 1)
        message += "<b>Bottleneck Analysis:</b>\n"
        message += f"Near High: {stats['near_high']/total*100:.0f}% | "
        message += f"Uptrend: {stats['uptrend']/total*100:.0f}% | "
        message += f"RSI: {stats['rsi_ok']/total*100:.0f}% | "
        message += f"Vol: {stats['volume_surge']/total*100:.0f}% | "
        message += f"Higher Lows: {stats['higher_lows']/total*100:.0f}%"

    send_telegram(message)

if __name__ == "__main__":
    send_daily_report()
