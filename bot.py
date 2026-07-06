import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# ---------- CONFIG ----------
TELEGRAM_TOKEN = os.environ['8799155611:AAHGhz1BdI9q9G8omDKA8Hx6pwfQXjTGBnw']
TELEGRAM_CHAT_ID = os.environ['8566469289']

# 150 large & mid-cap liquid stocks
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
    "JINDALSTEL.NS","JUBLFOOD.NS","LICHSGFIN.NS","LUPIN.NS","M&MFIN.NS",
    "MARICO.NS","MFSL.NS","MOTHERSON.NS","MPHASIS.NS","MRF.NS","MUTHOOTFIN.NS",
    "NAUKRI.NS","NAVINFLUOR.NS","NESTLEIND.NS","OBEROIRLTY.NS","OFSS.NS",
    "PAGEIND.NS","PERSISTENT.NS","PETRONET.NS","PFC.NS",
    "PIIND.NS","PNB.NS","POLYCAB.NS","POONAWALLA.NS",
    "PRESTIGE.NS","RAMCOCEM.NS","RBLBANK.NS","RECLTD.NS","SAIL.NS",
    "SBICARD.NS","SHREECEM.NS","SIEMENS.NS","SRF.NS","SUNTV.NS",
    "SYNGENE.NS","TATACHEM.NS","TATACOMM.NS","TATACONSUM.NS","TECHM.NS",
    "TIINDIA.NS","TRENT.NS","TVSMOTOR.NS","UPL.NS","YESBANK.NS",
    "ZEEL.NS","ZOMATO.NS","PAYTM.NS","POLICYBZR.NS","NYKAA.NS","DELHIVERY.NS"
]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def compute_technicals(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    close = df['Close']; high = df['High']; low = df['Low']; vol = df['Volume']
    df['ema50'] = close.ewm(span=50, adjust=False).mean()
    # ATR
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, 1)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_avg20'] = vol.rolling(20).mean()
    df['high20'] = high.rolling(20).max()
    return df

def get_fundamentals(symbol):
    try:
        info = yf.Ticker(symbol).info
        pe = info.get('trailingPE')
        de = info.get('debtToEquity')
        return {'pe': pe, 'debt_equity': de}
    except:
        return None

def scan_stocks():
    picks = []
    for sym in SYMBOLS:
        try:
            # Download 6 months of daily data for indicators
            df = yf.download(sym, period="6mo", interval="1d", progress=False)
            if len(df) < 100:
                continue
            df = compute_technicals(df)
            latest = df.iloc[-1]

            # --- TECHNICAL CONDITIONS (based on yesterday's close) ---
            # 1. Price > 50-day EMA (uptrend)
            if latest['Close'] <= latest['ema50']:
                continue
            # 2. RSI between 40-65 (momentum but not overbought)
            if not (40 < latest['rsi'] < 65):
                continue
            # 3. Volume > 1.2x average (buying interest)
            if latest['Volume'] < 1.2 * latest['vol_avg20']:
                continue
            # 4. Within 3% of 20-day high (ready to breakout)
            if latest['Close'] < latest['high20'] * 0.97:
                continue

            # --- BASIC FUNDAMENTAL FILTER (skip if missing) ---
            fund = get_fundamentals(sym)
            if fund:
                if fund['pe'] and fund['pe'] > 30:
                    continue
                if fund['debt_equity'] and fund['debt_equity'] > 2.0:
                    continue

            # All checks passed – calculate trade levels
            entry = round(latest['Close'], 2)
            atr = round(latest['atr'], 2)
            sl = round(entry - 2 * atr, 2)
            target1 = round(entry + 4 * atr, 2)
            target2 = round(entry + 6 * atr, 2)

            picks.append({
                'symbol': sym.replace('.NS',''),
                'entry': entry,
                'sl': sl,
                'target1': target1,
                'target2': target2,
                'rsi': round(latest['rsi'], 1),
                'volume': round(latest['Volume'] / latest['vol_avg20'], 1)
            })
        except Exception as e:
            continue

    # Sort by volume ratio (strongest first) and take top 5
    picks.sort(key=lambda x: x['volume'], reverse=True)
    return picks[:5]

def send_daily_report():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")

    picks = scan_stocks()

    if picks:
        msg = f"<b>🔥 DAILY TOP 5 STOCKS</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"
        for i, p in enumerate(picks, 1):
            msg += (
                f"<b>{i}. {p['symbol']}</b>\n"
                f"   💰 Entry: ₹{p['entry']}  |  🛑 SL: ₹{p['sl']}\n"
                f"   🎯 Target 1: ₹{p['target1']}  |  Target 2: ₹{p['target2']}\n"
                f"   📊 RSI: {p['rsi']}  |  Vol: {p['volume']}x\n\n"
            )
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "⚠️ <b>Paper trade first.</b> Use strict SL. Only 2% capital per trade."
    else:
        msg = f"<b>📭 NO SIGNALS TODAY</b>\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"
        msg += "No stocks passed all filters.\n"
        msg += "Market is either too weak or too extended.\n"
        msg += "Cash is a position. Patience is profit."

    send_telegram(msg)

if __name__ == "__main__":
    send_daily_report()
