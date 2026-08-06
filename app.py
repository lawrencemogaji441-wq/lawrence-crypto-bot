from flask import Flask
import requests, os
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_price_and_ma(symbol):
    try:
        # Price
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        price = float(requests.get(url, timeout=10).json()['result']['list'][0]['lastPrice'])
        # 15m candles for MA
        kline_url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=15&limit=30"
        klines = requests.get(kline_url, timeout=10).json()['result']['list']
        closes = [float(k[4]) for k in reversed(klines)]
        ma7 = sum(closes[-7:]) / 7
        ma14 = sum(closes[-14:]) / 14
        
        if price > ma7 and ma7 > ma14:
            sig = "LONG"
            direction = "BUY 🟢"
        elif price < ma7 and ma7 < ma14:
            sig = "SHORT"
            direction = "SELL 🔴"
        else:
            sig = "WAIT"
            direction = "WAIT 🟡"
        return price, ma7, ma14, sig, direction
    except:
        return 0,0,0,"WAIT","WAIT"

def build_pro_text(symbol_name, symbol_code, price, sig, direction, now):
    # Lagos time + Martingale 3 steps
    m1 = now + timedelta(minutes=1)
    m2 = now + timedelta(minutes=2)
    tp = price * 1.02 if sig=="LONG" else price * 0.98
    sl = price * 0.99 if sig=="LONG" else price * 1.01
    
    return f"""📡 Lawrence Signal - {sig}
⏰ Lagos: {now.strftime('%I:%M %p')}
Trade: {symbol_name}/USDT - Perpetual
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
            lagos = pytz.timezone("Africa/Lagos")
            now = datetime.now(lagos)
        except:
            now = datetime.utcnow() + timedelta(hours=1)

        # Get all 3
        eth_p, eth_ma7, eth_ma14, eth_sig, eth_dir = get_price_and_ma("ETHUSDT")
        btc_p, btc_ma7, btc_ma14, btc_sig, btc_dir = get_price_and_ma("BTCUSDT")
        sol_p, sol_ma7, sol_ma14, sol_sig, sol_dir = get_price_and_ma("SOLUSDT")

        # If SOL screenshot like yours (73.20 below MA) → it will auto show SHORT!
        
        final_text = ""
        if eth_sig != "WAIT":
            final_text += build_pro_text("ETH", "ETHUSDT", eth_p, eth_sig, eth_dir, now) + "\n"
        if btc_sig != "WAIT":
            final_text += build_pro_text("BTC", "BTCUSDT", btc_p, btc_sig, btc_dir, now) + "\n"
        if sol_sig != "WAIT":
            final_text += build_pro_text("SOL", "SOLUSDT", sol_p, sol_sig, sol_dir, now)

        if not final_text:
            final_text = f"⏰ {now.strftime('%I:%M %p')} WAT - No clear signal, WAIT 🟡"

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": final_text}, timeout=10)
        print(resp.text)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/')
def home():
    return "Lawrence PRO MA LIVE - ETH BTC SOL", 200

@app.route('/price')
def price():
    send_signal()
    return "OK", 200

@app.route('/test')
def test():
    send_signal()
    return "Sent PRO", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
