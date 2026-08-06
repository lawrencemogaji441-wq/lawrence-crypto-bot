        from flask import Flask
import requests, os
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_signal(symbol):
    try:
        # Price
        p_url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        price = float(requests.get(p_url, timeout=10).json()['result']['list'][0]['lastPrice'])
        # Candles
        k_url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=15&limit=30"
        klines = requests.get(k_url, timeout=10).json()['result']['list']
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

def make_text(name, price, sig, direction, now):
    m1 = now + timedelta(minutes=1)
    m2 = now + timedelta(minutes=2)
    # CORRECT TP/SL
    if sig == "LONG":
        tp = price * 1.02
        sl = price * 0.99
    else:
        tp = price * 0.98
        sl = price * 1.01

    return f"""📡 Lawrence Signal - {sig}
⏰ Lagos: {now.strftime('%I:%M %p')}
Trade: {name}/USDT - Perpetual
Direction: {direction}
Price: ${price:.2f}
TP: ${tp:.2f} | SL: ${sl:.2f}
5x Isolated - Bybit
Martingale: {now.strftime('%I:%M %p')}, {m1.strftime('%I:%M %p')}, {m2.strftime('%I:%M %p')}
"""

def send_signal():
    try:
        try:
            import pytz
            now = datetime.now(pytz.timezone("Africa/Lagos"))
        except:
            now = datetime.utcnow() + timedelta(hours=1)

        eth_p, eth_sig, eth_dir = get_signal("ETHUSDT")
        btc_p, btc_sig, btc_dir = get_signal("BTCUSDT")
        sol_p, sol_sig, sol_dir = get_signal("SOLUSDT")

        full = ""
        if eth_sig!= "WAIT":
            full += make_text("ETH", eth_p, eth_sig, eth_dir, now) + "\n\n"
        if btc_sig!= "WAIT":
            full += make_text("BTC", btc_p, btc_sig, btc_dir, now) + "\n\n"
        if sol_sig!= "WAIT":
            full += make_text("SOL", sol_p, sol_sig, sol_dir, now)

        if full == "":
            full = f"⏰ {now.strftime('%I:%M %p')} WAT - Market sideways, WAIT 🟡"

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": full}, timeout=10)
        return True
    except Exception as e:
        print(e)
        return False

@app.route('/')
def home():
    return "Lawrence Sniper PRO LIVE", 200

@app.route('/price')
def price():
    send_signal()
    return "OK", 200

@app.route('/test')
def test():
    send_signal()
    return "Sent", 200
