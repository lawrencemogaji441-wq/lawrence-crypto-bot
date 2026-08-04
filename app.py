import os
from flask import Flask
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Lawrence Bot LIVE! Go to /test and /price"

@app.route("/test")
def test():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat:
        return f"ERROR: Env vars missing! Token exists: {bool(token)} Chat exists: {bool(chat)}"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.get(url, params={"chat_id": chat, "text": "✅ Bot is working! - Lawrence"}, timeout=10)
        return f"Telegram API replied: {r.text}"
    except Exception as e:
        return f"Error sending: {str(e)}"

@app.route("/price")
def price():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    msg = "🔴 MA Signal: SHORT ETH\n💰 Entry: $2477\nTP $2440 | SL $2497 | 5x"
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.get(url, params={"chat_id": chat, "text": msg}, timeout=10)
    except:
        pass
    return msg

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
