              from flask import Flask
import requests, os, threading, time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import pytz

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === BEST SETTINGS FOR POCKET OPTION ===
PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X"
}
EXPIRY = 5
LAGOS_TZ = pytz.timezone("Africa/Lagos")
last_signal = {}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_signal(symbol_yf, pair_name):
    try:
        df = yf.download(symbol_yf, period="5d", interval="5m", progress=False, auto_adjust=True)
        if len(df) < 250:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        df['RSI'] = calc_rsi(df['Close'])
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower'] = df['SMA20'] - (df['STD20'] * 2)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        uptrend = last['EMA50'] > last['EMA200']
        downtrend = last['EMA50'] < last['EMA200']
        bullish = last['Close'] > last['Open']
        bearish = last['Close'] < last['Open']

        # BEST CALL / PUT LOGIC
        if uptrend and 35 < last['RSI'] < 55 and prev['RSI'] < last['RSI'] and bullish:
            return ("CALL", last)
        if downtrend and 45 < last['RSI'] < 65 and prev['RSI'] > last['RSI'] and bearish:
            return ("PUT", last)
        return None
    except Exception as e:
        print(f"Error {pair_name}: {e}")
        return None

def is_best_time():
    now = datetime.now(LAGOS_TZ)
    if now.weekday() >= 5:  # No forex Sat/Sun
        return False
    return 9 <= now.hour <= 16

def bot_loop():
    print("Lawrence Sniper FINAL BEST - Running 24/7...")
    send_telegram("✅ *Lawrence Sniper FINAL Started*\nPairs: EUR/USD, GBP/USD, USD/JPY\nChart: 5m | Expiry: 5m\nTime: 09:00-16:00 WAT\nMode: A+ setups only")

    while True:
        try:
            if not is_best_time():
                time.sleep(300)
                continue

            now = datetime.now(LAGOS_TZ)
            for pair_name, yf_sym in PAIRS.items():
                result = get_signal(yf_sym, pair_name)
                if result:
                    direction, candle = result
                    last = last_signal.get(pair_name, 0)
                    if time.time() - last > 900:  # 15 min cooldown per pair
                        price = round(float(candle['Close']), 5)
                        rsi = round(float(candle['RSI']), 1)
                        emoji = "🟢" if direction == "CALL" else "🔴"
                        next_entry = now + timedelta(minutes=5 - now.minute % 5)
                        next_entry = next_entry.replace(second=0, microsecond=0)

                        msg = f"""📡 *Lawrence Signal - {direction}* {emoji}
⏰ Lagos: {now.strftime('%I:%M %p')} WAT
Pair: {pair_name}
Direction: {direction} {emoji}
Price: {price} | RSI: {rsi}
Expiry: {EXPIRY} Minutes - Pocket Option
Enter At: {next_entry.strftime('%H:%M:00')} WAT
"""
                        send_telegram(msg)
                        last_signal[pair_name] = time.time()
            time.sleep(60)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(60)

# Start bot in background thread (so Flask keeps running)
threading.Thread(target=bot_loop, daemon=True).start()
      
@app.route('/')
def home():
    return "Lawrence Sniper Bot - BEST VERSION Running - EUR/USD, GBP/USD, USD/JPY"

if __name__ == "__main__":
    app.run(host="0.0.0.0", 
