from flask import Flask
import requests, os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

def send_signal():
    # Your ETH signal logic here - keep your existing logic
    # Example:
    try:
        # Get ETH price
        price_data = requests.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=ETHUSDT", timeout=10).json()
        price = price_data['result']['list'][0]['lastPrice']

        msg = f"📈 Lawrence ETH Signal\nPrice: ${price}\nTime: 4h MA OK\nEntry: {price}\nSL: calc\nTP: calc"

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return True
    except Exception as e:
        print(e)
        return False

@app.route('/')
def home():
    return "Lawrence Bot LIVE", 200

@app.route('/price')
def price():
    send_signal()
    return "OK", 200 # <--- THIS FIXES "Response too big"!!!

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
