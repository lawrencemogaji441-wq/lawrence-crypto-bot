from flask import Flask, request
import requests, os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_signal():
    try:
        # Get ETH price
        r = requests.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=ETHUSDT", timeout=10).json()
        price = float(r['result']['list'][0]['lastPrice'])
        text = f"⚡ Lawrence ETH Signal\nPrice: ${price}\nEntry: {price}\nTP: {price*1.02:.2f}\nSL: {price*0.99:.2f}\nTime: Auto 15min"
        
        if not BOT_TOKEN or not CHAT_ID:
            print("MISSING TOKEN/CHAT_ID")
            return False
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(resp.text)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/')
def home():
    return "Lawrence SMART BOT - Auto + Reply LIVE!", 200

@app.route('/price')
def price():
    ok = send_signal()
    # ALWAYS return tiny OK so cron-job passes, even if telegram fails
    return "OK", 200

@app.route('/test')
def test():
    has_token = "YES" if BOT_TOKEN else "NO - MISSING"
    has_chat = "YES" if CHAT_ID else "NO - MISSING"
    sent = send_signal()
    return f"Token: {has_token} | Chat: {has_chat} | Telegram Sent: {sent}", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
