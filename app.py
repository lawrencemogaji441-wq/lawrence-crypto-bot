from flask import Flask
import requests, os
from datetime import datetime, timedelta

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_price(symbol):
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        r = requests.get(url, timeout=10).json()
        return float(r['result']['list'][0]['lastPrice'])
    except:
        return 0

def send_signal():
    try:
        eth = get_price("ETHUSDT")
        btc = get_price("BTCUSDT")
        sol = get_price("SOLUSDT")

        # Time - Lagos (WAT)
        try:
            import pytz
            lagos = pytz.timezone("Africa/Lagos")
            now = datetime.now(lagos)
        except:
            now = datetime.utcnow() + timedelta(hours=1) # WAT = UTC+1

        expiry = now + timedelta(minutes=15)
        time_str = now.strftime("%I:%M %p")
        expiry_str = expiry.strftime("%I:%M %p")

        text = f"""⚡ LAWRENCE SNIPER - 15MIN

🟣 ETH: ${eth:.2f}
Entry: {eth:.2f} | TP: {eth*1.02:.2f} | SL: {eth*0.99:.2f}

🟠 BTC: ${btc:.2f}
Entry: {btc:.2f} | TP: {btc*1.02:.2f} | SL: {btc*0.99:.2f}

🔵 SOL: ${sol:.2f}
Entry: {sol:.2f} | TP: {sol*1.02:.2f} | SL: {sol*0.99:.2f}

⏰ Entry: {time_str} WAT
⏳ Expiry: {expiry_str} WAT (15min)
"""

        if not BOT_TOKEN or not CHAT_ID:
            print("Missing BOT_TOKEN or CHAT_ID")
            return False

        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(api_url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(f"Telegram Response: {resp.text}")
        return resp.status_code == 200

    except Exception as e:
        print(f"Error in send_signal: {e}")
        return False

@app.route('/')
def home():
    return "Lawrence MULTI BOT LIVE - ETH BTC SOL - 15MIN!", 200

@app.route('/price')
def price():
    success = send_signal()
    return ("OK - Signal Sent" if success else "FAILED") + " - 200", 200

@app.route('/test')
def test():
    has_token = "YES" if BOT_TOKEN else "NO-MISSING"
    has_chat = "YES" if CHAT_ID else "NO-MISSING"
    sent = send_signal()
    return f"Token: {has_token} | Chat: {has_chat} | Telegram Sent: {sent}", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
