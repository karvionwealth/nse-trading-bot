import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# ============================================
# CONFIGURATION
# ============================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

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
    "ZEEL.NS","PAYTM.NS","POLICYBZR.NS","NYKAA.NS","DELHIVERY.NS"
]

STOP_LOSS_PCT = 0.15  # 15% stop-loss per stock
TOP_N = 10
MOMENTUM_MONTHS = 12

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_momentum_score(prices, symbol, current_date):
    """Calculate 12-month momentum, skipping last month"""
    end_date = current_date - pd.DateOffset(months=1)
    start_date = end_date - pd.DateOffset(months=MOMENTUM_MONTHS)
    
    end_dates = prices.index[prices.index <= end_date]
    start_dates = prices.index[prices.index <= start_date]
    
    if len(end_dates) == 0 or len(start_dates) == 0:
        return None
    
    try:
        p_end = float(prices.loc[end_dates[-1], symbol])
        p_start = float(prices.loc[start_dates[-1], symbol])
        if pd.notna(p_end) and pd.notna(p_start) and p_start > 0:
            return (p_end - p_start) / p_start * 100
    except:
        pass
    return None

def check_market_trend():
    """Check if Nifty is above 200-day MA"""
    try:
        nifty = yf.download("^NSEI", period="1y", progress=False)
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.droplevel(1)
        close = nifty['Close']
        ma200 = close.rolling(200).mean()
        return float(close.iloc[-1]) > float(ma200.iloc[-1])
    except:
        return True  # If can't check, stay invested

def generate_monthly_signal():
    """Main function: Generate top 10 momentum stocks for the month"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y")
    
    # Check market trend
    market_up = check_market_trend()
    
    if not market_up:
        message = f"""<b>⚠️ MARKET BEARISH - STAY IN CASH</b>
📅 {date_str}
━━━━━━━━━━━━━━━

Nifty is below its 200-day moving average.
The bot recommends:
• <b>SELL all current holdings</b>
• <b>Stay in CASH</b> until market recovers
• Wait for next month's signal

<b>Protection Mode Active 🛡️</b>"""
        send_telegram(message)
        return
    
    # Download price data for momentum calculation
    end_date = now.strftime('%Y-%m-%d')
    start_date = (now - timedelta(days=500)).strftime('%Y-%m-%d')
    
    momentum_scores = {}
    for sym in SYMBOLS:
        try:
            df = yf.download(sym, start=start_date, end=end_date, progress=False)
            if len(df) < 250:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            score = get_momentum_score(df['Close'].to_frame() if isinstance(df['Close'], pd.Series) else df, sym.replace('.NS',''), pd.Timestamp.now())
            if score is not None:
                # Get current price for the symbol
                current_price = float(df['Close'].iloc[-1])
                momentum_scores[sym] = {
                    'score': score,
                    'price': current_price
                }
        except:
            continue
    
    if len(momentum_scores) < TOP_N:
        send_telegram(f"⚠️ Insufficient data. Only {len(momentum_scores)} stocks available.")
        return
    
    # Sort and pick top N
    sorted_stocks = sorted(momentum_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    top_picks = sorted_stocks[:TOP_N]
    
    # Build message
    message = f"""<b>🔔 MONTHLY MOMENTUM PICKS</b>
📅 {date_str}
━━━━━━━━━━━━━━━
Market Status: 🟢 <b>BULLISH</b> (Nifty > 200-day MA)

<b>BUY THESE 10 STOCKS (Equal Weight):</b>

"""
    for i, (sym, data) in enumerate(top_picks, 1):
        name = sym.replace('.NS', '')
        price = data['price']
        momentum = data['score']
        stop_loss = round(price * (1 - STOP_LOSS_PCT), 2)
        
        message += f"""<b>{i}. {name}</b>
   Price: ₹{price:.2f}
   12M Momentum: {momentum:.1f}%
   🛑 Stop-Loss: ₹{stop_loss}
   
"""
    
    message += f"""━━━━━━━━━━━━━━━
<b>📋 INSTRUCTIONS:</b>
• Buy all 10 stocks TODAY at market price
• Equal amount in each (e.g., ₹10,000 each for ₹1L portfolio)
• Set Stop-Loss at 15% below entry for each stock
• Hold until next month's signal (first week of next month)
• If any stock hits stop-loss intra-month, SELL immediately

⚠️ <b>Max Risk Per Stock: 15%</b>
🛡️ <b>Portfolio Emergency Brake: If total portfolio down 20%, sell everything</b>

Next review: First week of next month"""
    
    send_telegram(message)

if __name__ == "__main__":
    generate_monthly_signal()
