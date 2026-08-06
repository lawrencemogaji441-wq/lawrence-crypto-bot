                from flask import Flask
import requests, os, threading
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_signal(symbol):
    try:
        p_url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        price = float(requests.get(p_url, timeout=5).json()['result']['list'][0]['lastPrice'])
        k_url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=15&limit=20"
        klines = requests.get(k_url, timeout=5).json()['result']['list']
        closes = [float(k[4]) for k in reversed(klines)]
        ma7 = sum(closes[-7:]) / 7
        ma14 = sum(closes[-14:]) / 14
        if price > ma7 and ma7 > ma14:
            return price, "LONG", "BUY 🟢"
        elif price < ma7 and ma7 < ma14:
            return price, "SHORT", "SELL 🔴"
        else:
            return price, "WAIT", "WAIT"
    except:
        return 0, "WAIT", "WAIT"

def do_send():
    try:
        try:
            import pytz
            now = datetime.now(pytz.timezone("Africa/Lagos"))
        except:
            now = datetime.utcnow() + timedelta(hours=1)

        msgs = []
        for sym, name in [("ETHUSDT","ETH"),("BTCUSDT","BTC"),("SOLUSDT","SOL")]:
            price, sig, direction = get_signal(sym)
            if sig!= "WAIT":
                m1 = now + timedelta(minutes=1)
                m2 = now + timedelta(minutes=2)
                tp = price*1.02 if sig=="LONG" else price*0.98
                sl = price*0.99 if sig=="LONG" else price*1.01
                text = f"📡 Lawrence Signal - {sig}\n⏰ Lagos: {now.strftime('%I:%M %p')}\nTrade: {name}/USDT - Perpetual\nDirection: {direction}\nPrice: ${price:.2f}\nTP: ${tp:.2f} | SL: ${sl:.2f}\n5x Isolated - Bybit\nMartingale: {now.strftime('%I:%M %p')}, {m1.strftime('%I:%M %p')}, {m2.strftime('%I:%M %p')}"
                msgs.append(text)

        final = "\n\n".join(msgs) if msgs else f"⏰ {now.strftime('%I:%M %p')} WAT - WAIT 🟡"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":final}, timeout=10)
    except Exception as e:
        print(e)

@app.route('/')
def home(): return "Lawrence PRO LIVE", 200

@app.route('/price')
def price():
    threading.Thread(target=do_send).start()
    return "OK", 200 # Returns instantly, cron sees OK

@app.route('/test')
def test():
    threading.Thread(target=do_send).start()
    return "Sent", 200
