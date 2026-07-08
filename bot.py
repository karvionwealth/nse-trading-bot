import os
import yfinance as yf
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 150+ NSE large & mid‑cap stocks
STOCKS = [
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

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def analyze_stocks():
    calls = []
    puts = []
    for stock in STOCKS:
        try:
            ticker = yf.Ticker(stock)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                continue
            current_price = hist['Close'].iloc[-1]
            sma = hist['Close'].rolling(window=5).mean().iloc[-1] if len(hist) >= 5 else current_price

            if current_price > sma * 1.01:
                target = round(current_price * 1.05, 2)
                stoploss = round(current_price * 0.97, 2)
                calls.append((stock.replace('.NS',''), current_price, target, stoploss))
            elif current_price < sma * 0.99:
                target = round(current_price * 0.95, 2)
                stoploss = round(current_price * 1.03, 2)
                puts.append((stock.replace('.NS',''), current_price, target, stoploss))
        except:
            continue
    return calls[:5], puts[:5]

def send_daily_report():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")

    calls, puts = analyze_stocks()

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

    message += "━━━━━━━━━━━━━━━\n⚠️ SL mandatory | Target: 5%"
    send_telegram(message)

if __name__ == "__main__":
    send_daily_report()
