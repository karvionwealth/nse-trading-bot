import sys
sys.path.insert(0, '.')   # ensure bot.py is importable

from bot import fetch_and_scan, morning_alert

print("Starting evening scan...")
fetch_and_scan()
print("Evening scan completed.")
print("Now running morning alert...")
morning_alert()
print("Done. Check your Telegram.")
