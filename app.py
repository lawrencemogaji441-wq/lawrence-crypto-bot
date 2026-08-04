
import os, time, requests
from flask import Flask
import threading

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "Lawrence Crypto Bot is LIVE 24/7 🚀"

@app.route("/test")
def test():
    if not BOT_TOKEN or not CHAT_ID:
        return "Add Env Vars on Render!"
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=Test from Render - Bot is Working!")
        return f"Sent! {r.text}"
    except Exception as e:
        return f"Error: {e}"

def crypto_loop():
    while True:
        try:
            if BOT_TOKEN and CHAT_ID:
                price = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").json()
                btc = price['bitcoin']['usd']
                requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=BTC Price: ${btc}")
        except:
            pass
        time.sleep(3600)

threading.Thread(target=crypto_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
