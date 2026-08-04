import os
import time
import requests
from flask import Flask
import threading

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)

def get_eth_prices():
    # Get last 30 candles for MA
    url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1m&limit=30"
    r = requests.get(url).json()
    closes = [float(c[4]) for c in r]
    price = closes[-1]
    ma7 = sum(closes[-7:]) / 7
    ma14 = sum(closes[-14:]) / 14
    ma28 = sum(closes[-28:]) / 28
    return price, ma7, ma14, ma28

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

@app.route("/")
def home():
    return "Lawrence ETH Bot LIVE - MA Signals Active!"

@app.route("/price")
def price():
    price, ma7, ma14, ma28 = get_eth_prices()

    if price < ma7:
        zone = "🔴 SHORT ZONE - Price below MA7"
        signal = "SHORT ETH"
        tp = price * 0.985
        sl = price * 1.008
    else:
        zone = "🟢 LONG ZONE - Price above MA7"
        signal = "LONG ETH"
        tp = price * 1.015
        sl = price * 0.992

    msg = f"""🔴 MA Signal: {signal}
💰 Entry: ${price:.2f}
🟡 MA7 {ma7:.2f} | 🔵 MA14 {ma14:.2f} | 🟣 MA28 {ma28:.2f}
Zone: {zone}
SHORT 5x Isolated | TP ${tp:.2f} | SL ${sl:.2f} | Hold Max 2h
🕐 {time.strftime('%H:%M UTC', time.gmtime())}"""

    send_msg(msg)
    return msg

def auto_signals():
    while True:
        try:
            # Send signal every 30 minutes
            price()
        except:
            pass
        time.sleep(1800) # 30 mins

# Start auto loop in background
threading.Thread(target=auto_signals, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
