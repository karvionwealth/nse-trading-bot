import os
import yfinance as yf
import requests
from datetime import datetime
import pytz

# Read from GitHub Secrets (DO NOT hardcode)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def analyze_stocks():
    """Analyze NSE stocks and generate signals"""
    stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS"
    ]
    
    calls = []
    puts = []
    
    for stock in stocks[:7]:  # Check top 7 stocks
        try:
            ticker = yf.Ticker(stock)
            hist = ticker.history(period="1mo")
            
            if len(hist) < 20:
                continue
            
            df = hist.copy()
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            last_price = df['Close'].iloc[-1]
            last_sma20 = df['SMA20'].iloc[-1]
            
            # Simple logic
            if last_price > last_sma20 * 1.01:
                target = round(last_price * 1.05, 2)
                stoploss = round(last_price * 0.97, 2)
                calls.append((stock.replace('.NS', ''), last_price, target, stoploss))
            elif last_price < last_sma20 * 0.99:
                target = round(last_price * 0.95, 2)
                stoploss = round(last_price * 1.03, 2)
                puts.append((stock.replace('.NS', ''), last_price, target, stoploss))
        except:
            continue
    
    return calls, puts

def send_daily_report():
    """Generate and send trading report"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d %B %Y, %I:%M %p")
    
    calls, puts = analyze_stocks()
    
    message = f"🤖 NSE TRADING SIGNALS\n📅 {date_str}\n━━━━━━━━━━━━━━━\n\n"
    
    if calls:
        message += f"📈 BUY (CALL) Signals:\n"
        for name, price, target, sl in calls:
            message += f"• {name}: ₹{price}\n  → Target: ₹{target} | SL: ₹{sl}\n\n"
    else:
        message += f"📈 No BUY signals today\n\n"
    
    if puts:
        message += f"📉 SELL (PUT) Signals:\n"
        for name, price, target, sl in puts:
            message += f"• {name}: ₹{price}\n  → Target: ₹{target} | SL: ₹{sl}\n\n"
    else:
        message += f"📉 No SELL signals today\n\n"
    
    message += f"━━━━━━━━━━━━━━━\n⚠️ SL mandatory | Target: 5%"
    send_telegram(message)

if __name__ == "__main__":
    send_daily_report()
