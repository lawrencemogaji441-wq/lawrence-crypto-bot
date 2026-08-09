    from flask import Flask
import threading, time, datetime, pytz, requests, yfinance as yf
import pandas as pd

# ==== PUT YOURS HERE ====
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

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
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        signals_sent += 1
    except Exception as e:
        print("Telegram error:", e)

def get_signal(pair_name, yf_symbol):
    try:
        df = yf.download(yf_symbol, period="2d", interval="5m", progress=False)
        if len(df) < 50:
            return None
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        df['RSI'] = 100 - (100 / (1 + df['Close'].diff().where(lambda x: x>0,0).rolling(14).mean() / -df['Close'].diff().where(lambda x: x<0,0).rolling(14).mean()))
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + 2*df['STD']
        df['Lower'] = df['SMA20'] - 2*df['STD']
        last = df.iloc[-1]
        prev = df.iloc[-2]
        uptrend = last['EMA50'] > last['EMA200']
        if uptrend and prev['RSI'] < 30 and last['RSI'] > 30 and last['Close'] < last['Lower']*1.001:
            return "CALL"
        if not uptrend and prev['RSI'] > 70 and last['RSI'] < 70 and last['Close'] > last['Upper']*0.999:
            return "PUT"
        return None
    except:
        return None

def sniper_loop():
    global last_scan, total_scans
    send_telegram("✅ Lawrence Sniper FINAL Started\nPairs: EUR/USD, GBP/USD, USD/JPY\nChart: 5m | Expiry: 5m\nTime: 09:00-16:00 WAT\nMode: A+ setups only")
    while True:
        try:
            now = datetime.datetime.now(TIMEZONE)
            last_scan = now.strftime("%I:%M:%S %p WAT")
            total_scans += 1
            if now.weekday() < 5 and START_HOUR <= now.hour < END_HOUR:
                for pair_name, yf_symbol in PAIRS.items():
                    if pair_name in last_signal_time:
                        if (now - last_signal_time[pair_name]).seconds < COOLDOWN_MIN*60:
                            continue
                    signal = get_signal(pair_name, yf_symbol)
                    if signal:
                        t1 = now.strftime("%I:%M %p")
                        t2 = (now + datetime.timedelta(minutes=1)).strftime("%I:%M %p")
                        t3 = (now + datetime.timedelta(minutes=2)).strftime("%I:%M %p")
                        emoji = "🟢" if signal=="CALL" else "🔴"
                        msg = f"🔥 Lawrence Sniper FINAL\nPair: {pair_name}\nAction: {signal} {emoji}\nLagos: {t1} WAT\nEnter At: {t1}, {t2}, {t3}\nExpiry: 5m | Chart: 5m\nReason: A+ Setup"
                        send_telegram(msg)
                        last_signal_time[pair_name] = now
            time.sleep(60)
        except:
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
