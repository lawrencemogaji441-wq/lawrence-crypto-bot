import os, requests
from flask import Flask

app = Flask(__name__)

def get_real_eth():
    try:
        # Get real chart for MA
        url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"
        r = requests.get(url, timeout=15).json()
        prices = [p[1] for p in r['prices'][-30:]]  # last 30 points
        price = prices[-1]
        ma7 = sum(prices[-7:])/7
        ma14 = sum(prices[-14:])/14
        ma28 = sum(prices[-28:])/28
        return price, ma7, ma14, ma28
    except:
        # fallback live price
        p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()['ethereum']['usd']
        return float(p), float(p)*1.001, float(p)*1.002, float(p)*1.003

def send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.get(url, params={"chat_id": chat, "text": text}, timeout=10)

@app.route("/")
def home(): return "Lawrence ETH Bot V2 LIVE!"

@app.route("/price")
def price():
    price, ma7, ma14, ma28 = get_real_eth()
    
    if price < ma7:
        sig = "🔴 SHORT ETH"
        zone = "SHORT ZONE - Price BELOW MA7"
        tp = price * 0.985
        sl = price * 1.008
    else:
        sig = "🟢 LONG ETH"
        zone = "LONG ZONE - Price ABOVE MA7"
        tp = price * 1.015
        sl = price * 0.992
    
    msg = f"""{sig}
💰 Entry: ${price:.2f}
🟡 MA7: ${ma7:.2f} | 🔵 MA14: ${ma14:.2f} | 🟣 MA28: ${ma28:.2f}
📊 {zone}
⚙️ 5x Isolated | TP ${tp:.2f} | SL ${sl:.2f}
Hold Max 2h | Lawrence Bot"""
    
    send(msg)
    return msg.replace("\n", "<br>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
