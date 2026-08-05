import os, requests
from flask import Flask
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

def send(t):
    try:
        token=os.environ.get("TELEGRAM_BOT_TOKEN"); chat=os.environ.get("TELEGRAM_CHAT_ID")
        requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={"chat_id":chat,"text":t}, timeout=10)
    except: pass

@app.route("/")
def home(): return "Lawrence BOT Lagos Time FIXED!"

@app.route("/price")
def price():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",timeout=10).json()
        eth=float(r['ethereum']['usd'])
    except: eth=3800.0
    
    # Use LAGOS TIME!
    lagos = pytz.timezone('Africa/Lagos')
    now = datetime.now(lagos)
    
    if (now.hour + now.minute) % 2 == 0:
        direction="BUY 🟢"; action="LONG"; tp=eth*1.02; sl=eth*0.99
    else:
        direction="SELL 🔴"; action="SHORT"; tp=eth*0.98; sl=eth*1.01

    t1 = now.strftime("%I:%M %p")
    t2 = (now + timedelta(minutes=1)).strftime("%I:%M %p")
    t3 = (now + timedelta(minutes=2)).strftime("%I:%M %p")

    msg=f"""📡 Lawrence Signal - {action}
⏰ Lagos Time: {t1}
Trade: ETH/USD
Direction: {direction}
Price: ${eth:.2f}
TP: ${tp:.2f} | SL: ${sl:.2f}
5x Isolated

📡 XAU/USD (OTC)
Expiry: 5m
Entry: {t1}
Direction: {direction}
Martingale: {t1}, {t2}, {t3}"""

    send(msg)
    return msg.replace("\n","<br>")

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
