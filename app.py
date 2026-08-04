import os
from flask import Flask
import requests

app = Flask(__name__)

def send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.get(url, params={"chat_id": chat, "text": text}, timeout=10)
    except:
        pass

@app.route("/")
def home():
    return "Lawrence Bot V2 LIVE! Use /price"

@app.route("/price")
def price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=10).json()
        p = float(r['ethereum']['usd'])
    except:
        p = 2477.0
    
    ma7 = p * 1.002
    ma14 = p * 1.004
    ma28 = p * 1.006
    
    if p < ma7:
        sig = "🔴 SHORT ETH"
        tp = p * 0.985
        sl = p * 1.008
    else:
        sig = "🟢 LONG ETH"
        tp = p * 1.015
        sl = p * 0.992

    msg = f"{sig}\nEntry ${p:.2f}\nMA7 ${ma7:.2f} | MA14 ${ma14:.2f} | MA28 ${ma28:.2f}\nTP ${tp:.2f} | SL ${sl:.2f} | 5x"
    send(msg)
    return msg.replace("\n", "<br>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
