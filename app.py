import os
from flask import Flask
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": text})
        return True
    except:
        return False

@app.route("/")
def home():
    return "Lawrence Bot LIVE! Use /price or /test"

@app.route("/test")
def test():
    send_telegram("Bot is working! - Lawrence")
    return "Sent! Check Telegram"

@app.route("/price")
def price():
    # Simple fixed signal - we will add real MA after this works
    msg = "🔴 MA Signal: SHORT ETH\n💰 Entry: $2477.78\nMA7: 2482.89 | MA14: 2472.65 | MA28: 2472.89\nZone: SHORT ZONE\nTP $2440 | SL $2497 | 5x"
    send_telegram(msg)
    return msg

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
