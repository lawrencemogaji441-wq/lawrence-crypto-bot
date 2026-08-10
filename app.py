
        
import os
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY"]
YF_MAP = {"EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X"}
SCAN_INTERVAL = 60
TIMEFRAME = "5m"
EXPIRY = "5m"
TRADING_START = 9
TRADING_END = 21
WAT = timezone(timedelta(hours=1))

app = Flask(__name__)

last_scan = "Never"
scans_count = 0
signals_count = 0
wins = 0
losses = 0
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
.stat{font-size:18px;margin:5px}
</style>
</head>
<body>
<h1>LAWRENCE SNIPER v3 + RESULTS</h1>
<div class="card">
<div class="live">● BOT IS LIVE - AUTO RESULTS</div>
<p>Last Scan: {{last_scan}}</p>
<p>Scans: {{scans}} | Signals: {{signals}}</p>
<p class="stat">✅ Wins: {{wins}} | ❌ Losses: {{losses}}</p>
<p>WinRate: {{winrate}}%</p>
<p>Trading: {{trading}}</p>
</div>
<div class="card">
Pairs: EUR/USD, GBP/USD, USD/JPY<br>
Chart: 5m | Expiry: 5m<br>
Time: 09:00-21:00 WAT<br>
Mode: Grade A + Auto Result (5m later)
</div>
</body>
</html>
"""

def send_telegram(msg):
    global signals_count
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return r.status_code == 200
    except:
        return False

def check_result_later(pair, entry_price, action, entry_time_str):
    def job():
        global wins, losses
        time.sleep(320)  # wait 5m20s for candle to close
        try:
            yf_sym = YF_MAP[pair]
            df = yf.download(yf_sym, period="1d", interval="1m", progress=False)
            if df.empty:
                return
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Get last price after 5m
            # Find price ~5m after entry
            close_now = float(df['Close'].iloc[-1])
            # Compare
            if action == "CALL":
                won = close_now > entry_price
            else:
                won = close_now < entry_price
            
            if won:
                wins += 1
                result_msg = f"✅ WIN! \nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {close_now:.5f}\nProfit: +85%\nTime: {entry_time_str} -> 5m"
            else:
                losses += 1
                result_msg = f"❌ LOSS \nPair: {pair} {action}\nEntry: {entry_price:.5f}\nExit: {close_now:.5f}\nResult: -100%\nTime: {entry_time_str} -> 5m"
            send_telegram(result_msg)
        except Exception as e:
            print(f"Result check error: {e}")
    
    threading.Thread(target=job, daemon=True).start()

def get_signal(pair):
    try:
        yf_symbol = YF_MAP[pair]
        df = yf.download(yf_symbol, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']
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

        uptrend = curr_ema20 > curr_ema50
        downtrend = curr_ema20 < curr_ema50
        signal = None
        if uptrend and prev_rsi < 45 and curr_rsi >= 45 and curr_rsi < 65:
            signal = "CALL"
        elif downtrend and prev_rsi > 55 and curr_rsi <= 55 and curr_rsi > 35:
            signal = "PUT"
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
    global last_scan, scans_count, signals_count, is_trading_hours
    send_telegram("✅ Lawrence Sniper v3 Started\n+ AUTO WIN/LOSS CHECKER\nPairs: EUR/USD, GBP/USD, USD/JPY\nExpiry: 5m\nNow every signal will auto-check result after 5 mins!")
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
                        if key in last_signals and (time.time() - last_signals[key]) < 900:
                            continue
                        last_signals[key] = time.time()
                        signals_count += 1
                        msg = f"🔥 Lawrence Sniper FINAL\nPair: {result['pair']}\nAction: {result['action']} {'🟢' if result['action']=='CALL' else '🔴'}\nPrice: {result['price']:.5f}\nRSI: {result['rsi']:.1f}\nChart: {TIMEFRAME} | Expiry: {EXPIRY}\nTime: {last_scan}\n\n⏳ Result in 5 mins..."
                        send_telegram(msg)
                        check_result_later(result['pair'], result['price'], result['action'], last_scan)
                    time.sleep(2)
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(10)

@app.route("/")
def home():
    trading = "OPEN ✅" if is_trading_hours else "CLOSED (09-21 WAT)"
    total = wins+losses
    winrate = round((wins/total*100) if total>0 else 0, 1)
    return render_template_string(HTML, last_scan=last_scan, scans=scans_count, signals=signals_count, wins=wins, losses=losses, winrate=winrate, trading=trading)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
            
