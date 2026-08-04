import os, time, requests
from flask import Flask
import threading

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKE)
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID)

app = Flask(__name__)

@app.route("/")
def home():
    return "Lawrence Crypto Bot is LIVE 24/7!"

@app.route("/test")
def test():
    if not BOT_TOKEN or not CHAT_ID:
        return "Add Env Vars on Render!"
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": "🚀 Lawrence your bot is LIVE on Render 24/7! Use signals on Bybit app."}, timeout=10)
        return f"Sent! {r.text}"
    except Exception as e:
        return f"Error: {e}"

def crypto_loop():
    while True:
        time.sleep(60)

threading.Thread(target=crypto_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
