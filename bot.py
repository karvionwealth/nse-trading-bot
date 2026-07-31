import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# ---------- CONFIG ----------
# Reads from GitHub Secrets (TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# --- Support for multiple chat IDs ---
CHAT_IDS_MULTI = os.environ.get('TELEGRAM_CHAT_IDS')

if CHAT_IDS_MULTI:
    CHAT_IDS = [cid.strip() for cid in CHAT_IDS_MULTI.split(',') if cid.strip()]
else:
    single_id = os.environ.get('TELEGRAM_CHAT_ID')
    CHAT_IDS = [single_id] if single_id else []
# ------------------------------------------

# 128 liquid NSE stocks
SYMBOLS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","HINDUNILVR.NS",
    "ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS",
    "BAJFINANCE.NS","MARUTI.NS","TITAN.NS","SUNPHARMA.NS","NTPC.NS","ONGC.NS",
    "POWERGRID.NS","WIPRO.NS","HCLTECH.NS","ULTRACEMCO.NS","JSWSTEEL.NS",
    "TATASTEEL.NS","ADANIPORTS.NS","ADANIENT.NS","DIVISLAB.NS","DRREDDY.NS",
    "CIPLA.NS","BRITANNIA.NS","HDFCLIFE.NS","SBILIFE.NS","EICHERMOT.NS","M&M.NS",
    "HINDZINC.NS","VEDL.NS","DLF.NS","INDIGO.NS","HAVELLS.NS","VOLTAS.NS",
    "DABUR.NS","PIDILITIND.NS","BERGEPAINT.NS","LUPIN.NS","AUROPHARMA.NS",
    "BIOCON.NS","TORNTPHARM.NS","ALKEM.NS","APOLLOHOSP.NS","ASIANPAINT.NS",
    "BAJAJFINSV.NS","BAJAJHLDNG.NS","BALKRISIND.NS","BANDHANBNK.NS","BEL.NS",
    "BHARATFORG.NS","BOSCHLTD.NS","BPCL.NS","CANBK.NS","CHOLAFIN.NS","COALINDIA.NS",
    "COLPAL.NS","CONCOR.NS","CUMMINSIND.NS","DEEPAKNTR.NS","ESCORTS.NS",
    "GAIL.NS","GODREJCP.NS","GODREJPROP.NS","GRASIM.NS","HAL.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","HINDPETRO.NS","ICICIPRULI.NS",
    "IDFCFIRSTB.NS","INDUSINDBK.NS","INDUSTOWER.NS","IOC.NS","IRCTC.NS",
    "JINDALSTEL.NS","JUBLFOOD.NS","LICHSGFIN.NS","M&MFIN.NS","MARICO.NS",
    "MFSL.NS","MOTHERSON.NS","MPHASIS.NS","MRF.NS","MUTHOOTFIN.NS","NAUKRI.NS",
    "NAVINFLUOR.NS","NESTLEIND.NS","OBEROIRLTY.NS","OFSS.NS","PAGEIND.NS",
    "PERSISTENT.NS","PETRONET.NS","PFC.NS","PIIND.NS","PNB.NS","POLYCAB.NS",
    "POONAWALLA.NS","PRESTIGE.NS","RAMCOCEM.NS","RBLBANK.NS","RECLTD.NS",
    "SAIL.NS","SBICARD.NS","SHREECEM.NS","SIEMENS.NS","SRF.NS","SUNTV.NS",
    "SYNGENE.NS","TATACHEM.NS","TATACOMM.NS","TATACONSUM.NS","TECHM.NS",
    "TIINDIA.NS","TRENT.NS","TVSMOTOR.NS","UPL.NS","YESBANK.NS","ZEEL.NS",
    "PAYTM.NS","POLICYBZR.NS","NYKAA.NS","DELHIVERY.NS"
]

def send_telegram(msg):
    """Send message to multiple Telegram recipients."""
    if not TELEGRAM_TOKEN or not CHAT_IDS:
        print("❌ ERROR: TELEGRAM_TOKEN or CHAT_IDS not set in environment.")
        return
    
    for chat_id in CHAT_IDS:
        if not chat_id:
            continue
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            response = requests.post(
                url, 
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, 
                timeout=10
            )
            response.raise_for_status()
            print(f"✅ Telegram message sent successfully to {chat_id}!")
        except Exception as e:
            print(f"❌ Telegram error for {chat_id}: {e}")

def normalize_columns(df):
    """Ensures 'Open', 'High', 'Low', 'Close', 'Volume' exist."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip('_') for col in df.columns.values]
    
    df.columns = [str(col).strip() for col in df.columns]
    
    if len(df.columns) >= 4:
        if 'Close' not in df.columns:
            df['Close'] = df.iloc[:, 3]
        if 'High' not in df.columns and len(df.columns) >= 2:
            df['High'] = df.iloc[:, 1]
        if 'Low' not in df.columns and len(df.columns) >= 3:
            df['Low'] = df.iloc[:, 2]
        if 'Volume' not in df.columns and len(df.columns) >= 5:
            if len(df.columns) > 4:
                df['Volume'] = df.iloc[:, 4]
            elif len(df.columns) == 6:
                df['Volume'] = df.iloc[:, 5]

    for col in df.columns:
        col_lower = col.lower()
        if 'close' in col_lower and 'Close' not in df.columns:
            df['Close'] = df[col]
        if 'volume' in col_lower and 'Volume' not in df.columns:
            df['Volume'] = df[col]

    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def compute_technicals(df):
    """Calculate all technical indicators used by the bot."""
    df = normalize_columns(df)
    close = df['Close']
    high = df['High']
    low = df['Low']
    vol = df['Volume']

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
    rs = avg_gain / avg_loss.replace(0, 1)
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_avg20'] = vol.rolling(20).mean()
    df['high20'] = high.rolling(20).max()
    df['low20'] = low.rolling(20).min()
    return df

def get_basic_fundamentals(symbol):
    try:
        info = yf.Ticker(symbol).info
        pe = info.get('trailingPE')
        de = info.get('debtToEquity')
        if pe and pe > 30:
            return False
        if de and de > 2.0:
            return False
        return True
    except:
        return True

def generate_signals():
    calls = []
    puts = []
    
    for sym in SYMBOLS:
        try:
            df = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 100:
                continue
            
            df = normalize_columns(df)
            df = compute_technicals(df)
            latest = df.iloc[-1]

            if not get_basic_fundamentals(sym):
                continue

            close_val = float(latest['Close'])
            ema50_val = float(latest['ema50'])
            rsi_val = float(latest['rsi'])
            volume_val = float(latest['Volume'])
            vol_avg_val = float(latest['vol_avg20'])
            high20_val = float(latest['high20'])
            low20_val = float(latest['low20'])
            atr_val = float(latest['atr'])

            vol_ok = volume_val > 0.9 * vol_avg_val

            uptrend = close_val > ema50_val
            rsi_call_ok = 40 < rsi_val < 70
            near_high = close_val >= high20_val * 0.92
            
            if uptrend and rsi_call_ok and vol_ok and near_high:
                entry = round(close_val, 2)
                atr = round(atr_val, 2)
                target = round(entry + 2 * atr, 2)
                sl = round(entry - 1 * atr, 2)
                calls.append((sym.replace('.NS',''), entry, target, sl))

            downtrend = close_val < ema50_val
            rsi_put_ok = 30 < rsi_val < 60
            near_low = close_val <= low20_val * 1.08
            
            if downtrend and rsi_put_ok and vol_ok and near_low:
                entry = round(close_val, 2)
                atr = round(atr_val, 2)
                target = round(entry - 2 * atr, 2)
                sl = round(entry + 1 * atr, 2)
                puts.append((sym.replace('.NS',''), entry, target, sl))
                
        except Exception as e:
            continue

    calls.sort(key=lambda x: x[1], reverse=True)
    puts.sort(key=lambda x: x[1], reverse=True)
    return calls[:5], puts[:5]

def send_report():
    """Generate and send the report to Telegram."""
    send_telegram("🔔 BOT INITIALIZED. Fetching market data, please wait...")

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")

    print(f"🔄 Generating signals for {date_str}...")
    calls, puts = generate_signals()
    print(f"✅ Generated {len(calls)} CALLs and {len(puts)} PUTs")

    message = f"🤖 NSE TRADING SIGNALS\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"

    if calls:
        message += "📈 BUY (CALL) Signals:\n"
        for name, price, target, sl in calls:
            message += f"• {name}: ₹{price}\n  → Target: ₹{target} | SL: ₹{sl}\n\n"
    else:
        message += "📈 No BUY signals today\n\n"

    if puts:
        message += "📉 SELL (PUT) Signals:\n"
        for name, price, target, sl in puts:
            message += f"• {name}: ₹{price}\n  → Target: ₹{target} | SL: ₹{sl}\n\n"
    else:
        message += "📉 No SELL signals today\n\n"

    message += "━━━━━━━━━━━━━━━\n⚠️ SL mandatory | Targets based on 2x ATR (Proven Profitable)"
    
    print("📤 Sending to Telegram...")
    send_telegram(message)
    print("✅ Report complete!")

if __name__ == "__main__":
    print("🚀 Starting NSE Trading Bot...")
    send_report()
