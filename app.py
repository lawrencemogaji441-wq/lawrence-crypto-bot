
import os
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY"]
YF_MAP = {"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X"}
SCAN_INTERVAL = 60
TIMEFRAME = "5m"
EXPIRY = "5m"
TRADING_START = 9
TRADING_END = 21  # Extended to 9pm so you get more signals
WAT = timezone(timedelta(hours=1))

app = Flask(__name__)

last_scan = "Never"
scans_count = 0
signals_count = 0
last_signals = {}
is_trading_hours = True

HTML = """
<!DOCTYPE html>
<html>
<head><title>Lawrence Sniper FINAL</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Arial;background:#0a0e1a;color:white;text-align:center;padding:30px}
.card{background:#1a2332;padding:20px;border-radius:15px;margin:15px auto;max-width:500px;border:2px solid #00ff88}
.live{color:#00ff88;font-weight:bold;font-size:20px}
</style>
</head>
<body>
<h1>LAWRENCE SNIPER FINAL v2</h1>
<div class="card">
<div class="live">● BOT IS LIVE - LOOSE MODE</div>
<p>Last Scan: {{last_scan}}</p>
<p>Scans: {{scans}} | Real Signals: {{signals}}</p>
<p>Trading: {{trading}}</p>
</div>
<div class="card">
Pairs: EUR/USD, GBP/USD, USD/JPY<br>
Chart: 5m | Expiry: 5m<br>
Time: 09:00-21:00 WAT<br>
Mode: Grade A - More Signals
</div>
</body>
</html>
"""

def send_telegram(msg):
    global signals_count
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing BOT_TOKEN or CHAT_ID")
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        if r.status_code == 200:
            # Only count real CALL/PUT as signals
            if "CALL" in msg or "PUT" in msg:
                signals_count += 1
            return True
    except Exception as e:
        print(f"Telegram error: {e}")
    return False

def get_signal(pair):
    try:
        yf_symbol = YF_MAP[pair]
        df = yf.download(yf_symbol, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']
        # Indicators - LOOSE MODE
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        curr_price = float(close.iloc[-1])
        curr_rsi = float(rsi.iloc[-1])
        prev_rsi = float(rsi.iloc[-2])
        curr_ema20 = float(ema20.iloc[-1])
        curr_ema50 = float(ema50.iloc[-1])

        # LOOSE LOGIC - will give many signals
        uptrend = curr_ema20 > curr_ema50
        downtrend = curr_ema20 < curr_ema50

        signal = None
        # CALL: Uptrend + RSI crossing up 45
        if uptrend and prev_rsi < 45 and curr_rsi >= 45 and curr_rsi < 65:
            signal = "CALL"
        # PUT: Downtrend + RSI crossing down 55
        elif downtrend and prev_rsi > 55 and curr_rsi <= 55 and curr_rsi > 35:
            signal = "PUT"
        # Extra: Strong momentum
        elif curr_rsi > 50 and curr_rsi < 60 and uptrend and prev_rsi < curr_rsi:
            signal = "CALL"
        elif curr_rsi < 50 and curr_rsi > 40 and downtrend and prev_rsi > curr_rsi:
            signal = "PUT"

        if signal:
            return {"pair": pair, "action": signal, "price": curr_price, "rsi": curr_rsi}
        return None
    except Exception as e:
        print(f"Error {pair}: {e}")
        return None

def bot_loop():
    global last_scan, scans_count, is_trading_hours
    print("Bot loop started - LOOSE MODE")
    send_telegram("✅ Lawrence Sniper FINAL Started\nPairs: EUR/USD, GBP/USD, USD/JPY\nChart: 5m | Expiry: 5m\nTime: 09:00-21:00 WAT\nMode: Grade A - More Signals")
    while True:
        try:
            now_wat = datetime.now(WAT)
            is_trading_hours = TRADING_START <= now_wat.hour < TRADING_END
            last_scan = now_wat.strftime("%I:%M:%S %p WAT")
            if is_trading_hours:
                scans_count += 1
                for pair in PAIRS:
                    result = get_signal(pair)
                    if result:
                        key = f"{result['pair']}_{result['action']}"
                        # Prevent spam: 15 min cooldown per pair
                        if key in last_signals and (time.time() - last_signals[key]) < 900:
                            continue
                        last_signals[key] = time.time()
                        msg = f"🔥 Lawrence Sniper FINAL\nPair: {result['pair']}\nAction: {result['action']} {'🟢' if result['action']=='CALL' else '🔴'}\nPrice: {result['price']:.5f}\nRSI: {result['rsi']:.1f}\nChart: {TIMEFRAME} | Expiry: {EXPIRY}\nTime: {last_scan}"
                        send_telegram(msg)
                        print(f"SIGNAL: {msg}")
                    time.sleep(2)
            else:
                print(f"Outside trading hours: {last_scan}")
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(10)

@app.route("/")
def home():
    trading = "OPEN ✅" if is_trading_hours else "CLOSED (09-21 WAT)"
    return render_template_string(HTML, last_scan=last_scan, scans=scans_count, signals=signals_count, trading=trading)

# Start bot thread
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
