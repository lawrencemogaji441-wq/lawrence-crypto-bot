    from flask import Flask
import threading
import time
import datetime
import pytz
import requests
import yfinance as yf
import pandas as pd
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X"
}

TIMEZONE = pytz.timezone('Africa/Lagos')
START_HOUR = 9
END_HOUR = 16
COOLDOWN_MIN = 10

app = Flask(__name__)
last_scan = "Never"
total_scans = 0
signals_sent = 0
last_signal_time = {}
start_time = datetime.datetime.now(TIMEZONE)

def send_telegram(text):
    global signals_sent
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("Missing BOT_TOKEN or CHAT_ID")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        signals_sent += 1
    except Exception as e:
        print(e)

def get_signal(pair_name, yf_symbol):
    try:
        df = yf.download(yf_symbol, period="2d", interval="5m", progress=False)
        if df is None or len(df) < 50:
            return None
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + 2 * df['STD']
        df['Lower'] = df['SMA20'] - 2 * df['STD']
        last = df.iloc[-1]
        prev = df.iloc[-2]
        uptrend = float(last['EMA50']) > float(last['EMA200'])
        if uptrend and float(prev['RSI']) < 32 and float(last['RSI']) > 32:
            if float(last['Close']) <= float(last['Lower']) * 1.002:
                return "CALL"
        if not uptrend and float(prev['RSI']) > 68 and float(last['RSI']) < 68:
            if float(last['Close']) >= float(last['Upper']) * 0.998:
                return "PUT"
        return None
    except Exception:
        return None

def sniper_loop():
    global last_scan, total_scans
    time.sleep(5)
    send_telegram("✅ Lawrence Sniper FINAL Started\nPairs: EUR/USD, GBP/USD, USD/JPY\nChart: 5m | Expiry: 5m\nTime: 09:00-16:00 WAT\nMode: A+ setups only")
    while True:
        try:
            now = datetime.datetime.now(TIMEZONE)
            last_scan = now.strftime("%I:%M:%S %p WAT")
            total_scans += 1
            if now.weekday() < 5 and START_HOUR <= now.hour < END_HOUR:
                for pair_name, yf_symbol in PAIRS.items():
                    if pair_name in last_signal_time:
                        if (now - last_signal_time[pair_name]).seconds < COOLDOWN_MIN * 60:
                            continue
                    signal = get_signal(pair_name, yf_symbol)
                    if signal:
                        t1 = now.strftime("%I:%M %p")
                        t2 = (now + datetime.timedelta(minutes=1)).strftime("%I:%M %p")
                        t3 = (now + datetime.timedelta(minutes=2)).strftime("%I:%M %p")
                        emoji = "🟢" if signal == "CALL" else "🔴"
                        msg = f"🔥 Lawrence Sniper FINAL\nPair: {pair_name}\nAction: {signal} {emoji}\nLagos: {t1} WAT\nEnter At: {t1}, {t2}, {t3}\nExpiry: 5m | Chart: 5m\nReason: A+ Setup"
                        send_telegram(msg)
                        last_signal_time[pair_name] = now
            time.sleep(60)
        except Exception:
            time.sleep(60)

@app.route('/')
def home():
    uptime = datetime.datetime.now(TIMEZONE) - start_time
    return f"<h2>● BOT IS LIVE - FINAL</h2><p>Last Scan: {last_scan}</p><p>Uptime: {str(uptime).split('.')[0]}</p><p>Scans: {total_scans} | Signals: {signals_sent}</p><p>Pairs: EUR/USD, GBP/USD, USD/JPY | 5m | 09:00-16:00 | A+ only</p><meta http-equiv='refresh' content='10'>"

@app.route('/health')
def health():
    return "OK", 200

threading.Thread(target=sniper_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
