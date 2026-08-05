import os, requests
from flask import Flask, request
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_eth_price():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=ETHUSDT"
        r = requests.get(url, timeout=10).json()
        return float(r['result']['list'][0]['lastPrice'])
    except:
        return 1910.0

def send(text, chat=CHAT_ID):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": chat, "text": text}, timeout=10)
    except:
        pass

@app.route("/")
def home():
    return "Lawrence SMART BOT - Bybit LIVE!"

@app.route("/price")
def price():
    eth = get_eth_price()
    lagos = pytz.timezone('Africa/Lagos')
    now = datetime.now(lagos)
    if (now.hour + now.minute) % 2 == 0:
        direction = "BUY 🟢"
        action = "LONG"
        tp = eth * 1.02
        sl = eth * 0.99
    else:
        direction = "SELL 🔴"
        action = "SHORT"
        tp = eth * 0.98
        sl = eth * 1.01
    t1 = now.strftime("%I:%M %p")
    t2 = (now + timedelta(minutes=1)).strftime("%I:%M %p")
    t3 = (now + timedelta(minutes=2)).strftime("%I:%M %p")
    msg = f"📡 Lawrence Signal - {action}\n⏰ Lagos: {t1}\nTrade: ETH/USDT - Perpetual\nDirection: {direction}\nPrice: ${eth:.2f}\nTP: ${tp:.2f} | SL: ${sl:.2f}\n5x Isolated - Bybit\nMartingale: {t1}, {t2}, {t3}"
    send(msg)
    return msg.replace("\n", "<br>")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        cid = data["message"]["chat"]["id"]
        txt = data["message"].get("text", "")
        if "/price" in txt:
            price()
        else:
            send(f"Bot LIVE! ETH: ${get_eth_price():.2f}\nNext signal every 15min!", cid)
    except:
        pass
    return "ok"
