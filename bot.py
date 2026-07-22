import pandas as pd
import yfinance as yf
import numpy as np
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# ✅ OPTION A (RECOMMENDED) - CONFIGURATION
# ==========================================
TARGET_MULTIPLIER = 2.0   # Target = 2x ATR
SL_MULTIPLIER = 1.0       # Stop Loss = 1x ATR
HOLD_DAYS = 5             # Max hold period
# ==========================================

# --- YOUR EXACT STOCK LIST (129 stocks) ---
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
    "ZOMATO.NS","PAYTM.NS","POLICYBZR.NS","NYKAA.NS","DELHIVERY.NS"
]

def calculate_indicators(df):
    df['ema50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['high20'] = df['High'].rolling(20).max()
    df['low20'] = df['Low'].rolling(20).min()
    df['vol_avg20'] = df['Volume'].rolling(20).mean()
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, 1)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def backtest_atr_bot(stock_list, start_date, end_date):
    print("📥 Downloading Nifty data for Strict Filter...")
    nifty = yf.download("^NSEI", start=start_date, end=end_date, progress=False)
    nifty['SMA200'] = nifty['Close'].rolling(200).mean()
    
    all_trades = []
    total_stocks = len(stock_list)
    
    for idx, sym in enumerate(stock_list):
        print(f"⏳ Processing {idx+1}/{total_stocks}: {sym}")
        try:
            df = yf.download(sym, start=start_date, end=end_date, progress=False)
            if df.empty or len(df) < 250:
                continue
            df = calculate_indicators(df)
            
            for i in range(200, len(df) - HOLD_DAYS):
                row = df.iloc[i]
                signal_date = row.name.date()
                
                # Convert everything to Python float to kill any Series bugs
                close_val = float(row['Close'])
                ema50_val = float(row['ema50'])
                rsi_val = float(row['rsi'])
                volume_val = float(row['Volume'])
                vol_avg_val = float(row['vol_avg20'])
                high20_val = float(row['high20'])
                low20_val = float(row['low20'])
                atr_val = float(row['atr'])
                
                # Nifty Macro Check
                nifty_today = nifty[nifty.index.date == signal_date]
                if nifty_today.empty:
                    continue
                nifty_above_200 = float(nifty_today['Close'].iloc[0]) > float(nifty_today['SMA200'].iloc[0])
                
                vol_ok = volume_val > 0.9 * vol_avg_val
                
                # --- BUY (CALL) ---
                if (close_val > ema50_val and 40 < rsi_val < 70 and vol_ok and close_val >= high20_val * 0.92):
                    entry = close_val
                    target = entry + (TARGET_MULTIPLIER * atr_val)
                    sl = entry - (SL_MULTIPLIER * atr_val)
                    
                    future_high = float(df['High'].iloc[i+1:i+1+HOLD_DAYS].max())
                    future_low = float(df['Low'].iloc[i+1:i+1+HOLD_DAYS].min())
                    close_at_exit = float(df['Close'].iloc[i+HOLD_DAYS])
                    
                    if future_high >= target:
                        pnl = (target / entry - 1) * 100
                        result = "WIN (Target)"
                    elif future_low <= sl:
                        pnl = (sl / entry - 1) * 100
                        result = "LOSS (SL)"
                    else:
                        pnl = (close_at_exit / entry - 1) * 100
                        result = "EXIT (Time)"
                        
                    all_trades.append({
                        'Date': signal_date,
                        'Stock': sym.replace('.NS',''),
                        'Direction': 'BUY',
                        'Entry': round(entry, 2),
                        'Target': round(target, 2),
                        'SL': round(sl, 2),
                        'PnL_%': round(pnl, 2),
                        'Result': result,
                        'Nifty_Above_200': nifty_above_200
                    })
                
                # --- SELL (PUT) ---
                elif (close_val < ema50_val and 30 < rsi_val < 60 and vol_ok and close_val <= low20_val * 1.08):
                    entry = close_val
                    target = entry - (TARGET_MULTIPLIER * atr_val)
                    sl = entry + (SL_MULTIPLIER * atr_val)
                    
                    future_high = float(df['High'].iloc[i+1:i+1+HOLD_DAYS].max())
                    future_low = float(df['Low'].iloc[i+1:i+1+HOLD_DAYS].min())
                    close_at_exit = float(df['Close'].iloc[i+HOLD_DAYS])
                    
                    if future_low <= target:
                        pnl = (1 - target / entry) * 100
                        result = "WIN (Target)"
                    elif future_high >= sl:
                        pnl = (1 - sl / entry) * 100
                        result = "LOSS (SL)"
                    else:
                        pnl = (1 - close_at_exit / entry) * 100
                        result = "EXIT (Time)"
                        
                    all_trades.append({
                        'Date': signal_date,
                        'Stock': sym.replace('.NS',''),
                        'Direction': 'SELL',
                        'Entry': round(entry, 2),
                        'Target': round(target, 2),
                        'SL': round(sl, 2),
                        'PnL_%': round(pnl, 2),
                        'Result': result,
                        'Nifty_Above_200': nifty_above_200
                    })
                    
        except Exception as e:
            # Silently skip errors (ZOMATO.NS etc.)
            continue
    
    return pd.DataFrame(all_trades)

# ==========================================
# 🚀 RUN THE BACKTEST
# ==========================================
print("🚀 STARTING BACKTEST - OPTION A (2x Target, 1x SL)")
print(f"   Hold Period: {HOLD_DAYS} days")
print("   Date Range: 2024-01-01 to 2026-07-19\n")

df_trades = backtest_atr_bot(SYMBOLS, '2024-01-01', '2026-07-19')

# --- RESULTS ---
if df_trades.empty:
    print("\n❌ NO TRADES GENERATED. Try loosening the entry filters.")
else:
    bull_trades = df_trades[df_trades['Nifty_Above_200'] == True]
    bear_trades = df_trades[df_trades['Nifty_Above_200'] == False]

    print("\n" + "="*70)
    print(f"📊 TOTAL TRADES GENERATED: {len(df_trades)}")
    print("="*70)

    def print_stats(df, label):
        if df.empty:
            print(f"\n🔵 {label}: ❌ NO TRADES")
            return
        wins = df[df['Result'].str.contains('WIN')]
        losses = df[df['Result'].str.contains('LOSS')]
        time_exits = df[df['Result'].str.contains('EXIT')]
        
        print(f"\n🔵 {label}")
        print(f"   Total Trades: {len(df)}")
        print(f"   Win Rate: {len(wins)/len(df)*100:.1f}%")
        print(f"   Avg Win: {wins['PnL_%'].mean():.2f}%")
        print(f"   Avg Loss: {losses['PnL_%'].mean():.2f}%")
        print(f"   Avg Return Per Trade: {df['PnL_%'].mean():.2f}%")
        print(f"   Net Cumulative P&L (sum): ₹{df['PnL_%'].sum():.2f}")
        print(f"   Time Exits: {len(time_exits)} ({len(time_exits)/len(df)*100:.1f}%)")

    print_stats(bull_trades, "BULL MARKET (Nifty > 200 DMA)")
    print_stats(bear_trades, "BEAR MARKET (Nifty < 200 DMA)")

    # --- FINAL VERDICT ---
    if not bull_trades.empty:
        bull_pnl = bull_trades['PnL_%'].sum()
        if bull_pnl > 0:
            print("\n" + "="*70)
            print(f"🎉 OPTION A IS PROFITABLE IN BULL MARKETS! (+₹{bull_pnl:.2f})")
            print("   You can deploy this bot with confidence in bull markets.")
            print("   Keep the Strict Bot (Nifty > 200 DMA) as your gatekeeper.")
            print("="*70)
        else:
            print("\n" + "="*70)
            print(f"⚠️ OPTION A IS STILL NEGATIVE IN BULL MARKETS (-₹{abs(bull_pnl):.2f})")
            print("   Moving to OPTION D (1.5x Target, 1x SL) - Send me the numbers.")
            print("="*70)
