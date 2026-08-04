import os
from flask import Flask
import requestsBOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "Lawrence Bot is LIVE!"

@app.route("/test")
def test():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": "Bot is working!"}
    r = requests.get(url, params=data)
    return r.text

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
