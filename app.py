from flask import Flask
import requests, os
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_price_and_ma(symbol):
    try:
        # Get price
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        price = float(requests.get(url, timeout=10).json()['result']['list'][0]['lastPrice'])

        # Get candles for MA (15min x 30)
        kline_url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=15&limit=30"
        klines = requests.get(kline_url, timeout=10).json()['result']['list']
        # Bybit returns newest first, close price is index 4
        closes = [float(k[4]) for k in reversed(klines)]

        ma7 = sum(closes[-7:]) / 7
        ma14 = sum(closes[-14:]) / 14
        ma28 = sum(closes[-28:]) / 28 if len(closes) >=28 else ma14

        # Signal logic
        if price > ma7 and ma7 > ma14:
            signal = "🟢 LONG"
        elif price < ma7 and ma7 < ma14:
            signal = "🔴 SHORT"
        else:
            signal = "🟡 WAIT"

        return price, ma7, ma14, ma28, signal
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return 0,0,0,0,"WAIT"

def send_signal():
    try:
        eth_p, eth_ma7, eth_ma14, eth_ma28, eth_sig = get_price_and_ma("ETHUSDT")
        btc_p, btc_ma7, btc_ma14, btc_ma28, btc_sig = get_price_and_ma("BTCUSDT")
        sol_p, sol_ma7, sol_ma14, sol_ma28, sol_sig = get_price_and_ma("SOLUSDT")

        # Time
        try:
            import pytz
            lagos = pytz.timezone("Africa/Lagos")
            now = datetime.now(lagos)
        except:
            now = datetime.utcnow() + timedelta(hours=1)
        expiry = now + timedelta(minutes=15)

        text = f"""⚡ LAWRENCE SNIPER PRO - 15MIN

🟣 ETH: ${eth_p:.2f} - {eth_sig}
MA7:{eth_ma7:.2f} MA14:{eth_ma14:.2f}
Entry: {eth_p:.2f} | TP: {eth_p*1.02:.2f} | SL: {eth_p*0.99:.2f}

🟠 BTC: ${btc_p:.2f} - {btc_sig}
MA7:{btc_ma7:.2f} MA14:{btc_ma14:.2f}
Entry: {btc_p:.2f} | TP: {btc_p*1.02:.2f} | SL: {btc_p*0.99:.2f}

🔵 SOL: ${sol_p:.2f} - {sol_sig}
MA7:{sol_ma7:.2f} MA14:{sol_ma14:.2f}
Entry: {sol_p:.2f} | TP: {sol_p*1.02:.2f} | SL: {sol_p*0.99:.2f}

⏰ {now.strftime('%I:%M %p')} → {expiry.strftime('%I:%M %p')} WAT
"""

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(resp.text)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error send: {e}")
        return False

@app.route('/')
def home():
    return "Lawrence PRO MA BOT LIVE!", 200

@app.route('/price')
def price():
    send_signal()
    return "OK", 200

@app.route('/test')
def test():
    sent = send_signal()
    return f"Sent: {sent}", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
