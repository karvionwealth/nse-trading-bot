import os
import yfinance as yf
import requests
from datetime import datetime
import pytz

# Read from GitHub Secrets
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def analyze_stocks():
    """Use current price (latest available) to generate signals."""
    stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS"
    ]
    calls = []
    puts = []

    for stock in stocks[:7]:  # Limit to 7 stocks
        try:
            ticker = yf.Ticker(stock)
            # Get data for last 5 days (daily)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                continue

            # Use the most recent close as entry price (this is TODAY's price if market is open)
            current_price = hist['Close'].iloc[-1]
            # Calculate SMA of last 5 closes
            sma = hist['Close'].rolling(window=5).mean().iloc[-1] if len(hist) >= 5 else current_price

            # Generate signals based on price vs SMA
            if current_price > sma * 1.01:   # Bullish (above SMA)
                target = round(current_price * 1.05, 2)
                stoploss = round(current_price * 0.97, 2)
                calls.append((stock.replace('.NS', ''), current_price, target, stoploss))
            elif current_price < sma * 0.99: # Bearish (below SMA)
                target = round(current_price * 0.95, 2)
                stoploss = round(current_price * 1.03, 2)
                puts.append((stock.replace('.NS', ''), current_price, target, stoploss))
        except Exception as e:
            print(f"Error analyzing {stock}: {e}")
            continue

    return calls, puts

def send_daily_report():
    """Generate and send report with current price levels."""
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
